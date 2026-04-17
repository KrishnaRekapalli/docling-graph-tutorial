"""
Knowledge graph visualizer for docling-graph extraction output.

Usage:
    uv run python visualize_graph.py                        # latest run
    uv run python visualize_graph.py data/test_output/NVIDIAAn_pdf_.../docling_graph/graph.json

Produces:
    graph_pretty.html  — interactive pyvis (open in browser)
    graph_summary.png  — static matplotlib summary chart
"""

import json
import sys
from pathlib import Path
from collections import Counter, defaultdict

import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


# ── Colour palette ─────────────────────────────────────────────────────────────
#
# Colors are assigned dynamically from this palette based on graph topology:
#   • Root node (0 in-degree)  → ROOT_COLOR
#   • All other types          → cycled through PALETTE in order of frequency
# The same type name always maps to the same color within a single run.

ROOT_COLOR   = "#1a1a2e"   # dark navy — always used for the document root
PALETTE = [
    "#e94560",   # red
    "#0f3460",   # dark blue
    "#533483",   # purple
    "#16213e",   # slate navy
    "#2d6a4f",   # green
    "#b5451b",   # burnt orange
    "#1b4965",   # steel blue
    "#5c4033",   # brown
]


def build_color_map(G: nx.DiGraph) -> dict[str, str]:
    """
    Assign a color to each node type found in G.
    Root types (0 in-degree nodes) get ROOT_COLOR.
    All other types cycle through PALETTE ordered by frequency (most common first).
    Returns a dict: {class_name: hex_color}
    """
    # Identify root types — classes whose nodes have no incoming edges
    root_types: set[str] = set()
    for node_id, data in G.nodes(data=True):
        if G.in_degree(node_id) == 0:
            cls = data.get("__class__") or data.get("type", "")
            if cls:
                root_types.add(cls)

    # Count all types
    type_counts = Counter(
        d.get("__class__") or d.get("type", "unknown")
        for _, d in G.nodes(data=True)
    )

    color_map: dict[str, str] = {}
    palette_idx = 0

    for cls, _ in type_counts.most_common():
        if cls in root_types:
            color_map[cls] = ROOT_COLOR
        else:
            color_map[cls] = PALETTE[palette_idx % len(PALETTE)]
            palette_idx += 1

    color_map["default"] = "#555555"
    return color_map


# Populated lazily per-graph call (module-level cache for the current graph)
_color_map: dict[str, str] = {}


def _color(cls: str) -> str:
    return _color_map.get(cls, _color_map.get("default", "#555555"))


NODE_BORDER = {
    "default":         "#cccccc",
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def _node_label(node_id: str, data: dict) -> str:
    """Best human-readable label for a node."""
    cls = data.get("__class__") or data.get("type", "")
    candidates = [
        data.get("name"),
        data.get("title"),
        data.get("company"),
        data.get("fiscal_period"),
        data.get("insured_name"),       # InsuranceCertificate
        data.get("invoice_number"),     # Invoice
        data.get("policy_number"),      # Coverage
        data.get("coverage_type"),      # CoverageLimit fallback
        # FinancialMetric without name: use value
        (f"{cls}: {data['value']}" if data.get("value") and not data.get("name") else None),
    ]
    label = next((c for c in candidates if c and str(c).strip()), None)
    if label:
        # Truncate long labels
        return label if len(label) <= 35 else label[:32] + "…"
    # Last resort: strip the hash suffix
    return node_id.rsplit("_", 1)[0].replace("_", " ")


def _node_tooltip(node_id: str, data: dict) -> str:
    """Rich hover tooltip."""
    lines = []
    cls = data.get("__class__") or data.get("type", "")
    lines.append(f"<b>{cls}</b>")
    skip = {"id", "label", "type", "__class__", "key_products", "products",
            "segments", "partners", "key_metrics", "affects_segments"}
    for k, v in data.items():
        if k in skip or not v or v in ("[]", "{}"):
            continue
        lines.append(f"<b>{k}:</b> {v}")
    return "<br>".join(lines)


def _edge_label(data: dict) -> str:
    rel = data.get("relation") or data.get("label") or ""
    # Convert snake_case field names → readable
    mapping = {
        "key_metrics":      "HAS_METRIC",
        "segments":         "HAS_SEGMENT",
        "partners":         "HAS_PARTNER",
        "products":         "USES",
        "affects_segments": "AFFECTS",
        "risk_factors":     "HAS_RISK",
    }
    return mapping.get(rel, rel.upper() if rel else "")


def load_graph(path: Path) -> nx.DiGraph:
    with open(path) as f:
        data = json.load(f)
    G = nx.DiGraph()
    for node in data["nodes"]:
        node = dict(node)
        node_id = node.pop("id")
        G.add_node(node_id, **node)
    for edge in data["edges"]:
        G.add_edge(edge["source"], edge["target"],
                   relation=edge.get("relation") or edge.get("label", ""))
    return G


# ── HTML post-processing: legend + node panel ─────────────────────────────────

def _inject_legend_and_panel(out_path: Path, color_map: dict, G: nx.DiGraph) -> None:
    """Inject a color legend and a click-to-inspect node panel into the pyvis HTML."""
    from collections import Counter
    type_counts = Counter(
        d.get("__class__") or d.get("type", "?")
        for _, d in G.nodes(data=True)
    )

    # Build legend HTML rows
    legend_rows = ""
    for cls, count in type_counts.most_common():
        color = color_map.get(cls, "#555555")
        legend_rows += (
            f'<div style="display:flex;align-items:center;gap:8px;margin:4px 0">'
            f'<div style="width:14px;height:14px;border-radius:50%;background:{color};'
            f'border:1px solid #555;flex-shrink:0"></div>'
            f'<span style="color:#e6edf3;font-size:12px">{cls}</span>'
            f'<span style="color:#6e7681;font-size:11px">×{count}</span>'
            f'</div>'
        )

    inject = f"""
<style>
  #legend {{
    position:fixed; top:16px; right:16px; z-index:999;
    background:#161b22; border:1px solid #30363d; border-radius:8px;
    padding:12px 16px; min-width:160px;
    font-family: -apple-system, monospace;
  }}
  #legend h4 {{
    margin:0 0 8px 0; color:#e6edf3; font-size:12px;
    text-transform:uppercase; letter-spacing:.08em;
  }}
  #node-panel {{
    position:fixed; bottom:16px; left:16px; z-index:999;
    background:#161b22; border:1px solid #30363d; border-radius:8px;
    padding:14px 18px; min-width:220px; max-width:320px;
    font-family: -apple-system, monospace; display:none;
  }}
  #node-panel h4 {{
    margin:0 0 8px 0; color:#e94560; font-size:13px; font-weight:600;
  }}
  #node-panel table {{ border-collapse:collapse; width:100%; }}
  #node-panel td {{ padding:2px 6px; font-size:12px; color:#e6edf3; vertical-align:top; }}
  #node-panel td:first-child {{ color:#8b949e; white-space:nowrap; padding-right:10px; }}
  #close-panel {{
    position:absolute; top:8px; right:10px;
    color:#6e7681; cursor:pointer; font-size:16px; line-height:1;
  }}
  #close-panel:hover {{ color:#e6edf3; }}
</style>

<div id="legend">
  <h4>Node Types</h4>
  {legend_rows}
</div>

<div id="node-panel">
  <span id="close-panel" onclick="document.getElementById('node-panel').style.display='none'">✕</span>
  <h4 id="panel-title"></h4>
  <table id="panel-table"></table>
</div>

<script>
(function() {{
  var SKIP = new Set(["id","label","type","__class__","key_products","products",
                      "segments","partners","key_metrics","affects_segments",
                      "color","font","shape","size","title","x","y","physics",
                      "borderWidth","shadow","hidden"]);
  function waitForNetwork() {{
    if (typeof network === 'undefined') {{ setTimeout(waitForNetwork, 200); return; }}
    network.on("click", function(params) {{
      if (!params.nodes.length) return;
      var nodeId = params.nodes[0];
      var data = nodes.get(nodeId);
      if (!data) return;
      var cls = data.__class__ || data.type || "Node";
      document.getElementById("panel-title").textContent = cls;
      var rows = "";
      for (var k in data) {{
        if (SKIP.has(k)) continue;
        var v = data[k];
        if (!v || v === "[]" || v === "{{}}") continue;
        if (typeof v === "object") v = JSON.stringify(v);
        rows += "<tr><td>" + k + "</td><td>" + v + "</td></tr>";
      }}
      document.getElementById("panel-table").innerHTML = rows;
      document.getElementById("node-panel").style.display = "block";
    }});
  }}
  waitForNetwork();
}})();
</script>
"""

    html = out_path.read_text(encoding="utf-8")
    html = html.replace("</body>", inject + "\n</body>")
    out_path.write_text(html, encoding="utf-8")


# ── Interactive HTML (pyvis) ───────────────────────────────────────────────────

def make_interactive(G: nx.DiGraph, out_path: Path) -> None:
    global _color_map
    _color_map = build_color_map(G)

    from pyvis.network import Network

    net = Network(
        height="750px", width="100%",
        bgcolor="#0d1117", font_color="#e6edf3",
        directed=True,
        notebook=False,
        cdn_resources="inline",   # embed vis.js so it works offline and in VS Code notebooks
    )
    net.set_options("""
    {
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -8000,
          "centralGravity": 0.4,
          "springLength": 140,
          "springConstant": 0.06
        },
        "stabilization": {"iterations": 200}
      },
      "edges": {
        "arrows": {"to": {"enabled": true, "scaleFactor": 0.6}},
        "color": {"color": "#4a5568", "highlight": "#e94560"},
        "font": {"size": 10, "color": "#9ca3af", "strokeWidth": 0},
        "smooth": {"type": "curvedCW", "roundness": 0.1}
      },
      "nodes": {
        "borderWidth": 2,
        "shadow": true
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 150,
        "navigationButtons": true
      }
    }
    """)

    for node_id, data in G.nodes(data=True):
        cls = data.get("__class__") or data.get("type", "default")
        color = _color(cls)
        border = NODE_BORDER.get(cls, NODE_BORDER["default"])
        label = _node_label(node_id, data)
        size = 40 if cls.endswith("Earnings") else (28 if cls in ("BusinessSegment", "Partner") else 18)

        net.add_node(
            node_id,
            label=label,
            title="",   # disable native hover tooltip — panel handles this
            color={"background": color, "border": border, "highlight": {"background": "#e94560"}},
            size=size,
            font={"size": 13 if size >= 28 else 11},
            **{k: v for k, v in data.items()
               if k not in {"id", "label", "type", "__class__"}},
        )

    for src, tgt, data in G.edges(data=True):
        elabel = _edge_label(data)
        net.add_edge(src, tgt, label=elabel, title=elabel)

    net.save_graph(str(out_path))
    _inject_legend_and_panel(out_path, _color_map, G)
    print(f"Interactive graph → {out_path}")


# ── Static summary chart (matplotlib) ─────────────────────────────────────────

def make_summary_chart(G: nx.DiGraph, out_path: Path) -> None:
    global _color_map
    _color_map = build_color_map(G)

    type_counts = Counter(
        (d.get("__class__") or d.get("type", "Unknown"))
        for _, d in G.nodes(data=True)
    )
    rel_counts = Counter(
        _edge_label(d) or "LINKED"
        for _, _, d in G.edges(data=True)
    )

    fig, axes = plt.subplots(1, 3, figsize=(16, 6))
    fig.patch.set_facecolor("#0d1117")
    for ax in axes:
        ax.set_facecolor("#161b22")
        ax.tick_params(colors="#e6edf3")
        for spine in ax.spines.values():
            spine.set_edgecolor("#30363d")

    text_kw = dict(color="#e6edf3")

    # 1. Node type distribution
    ax = axes[0]
    types = list(type_counts.keys())
    counts = [type_counts[t] for t in types]
    colors = [_color(t) for t in types]
    bars = ax.barh(types, counts, color=colors, edgecolor="#30363d")
    ax.set_title("Node types", **text_kw, fontsize=13, pad=10)
    ax.set_xlabel("Count", **text_kw)
    ax.tick_params(axis='y', labelsize=10, colors="#e6edf3")
    ax.tick_params(axis='x', colors="#e6edf3")
    for bar, count in zip(bars, counts):
        ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
                str(count), va="center", fontsize=10, color="#e6edf3")

    # 2. Edge relation distribution
    ax = axes[1]
    rels = list(rel_counts.keys())
    rcounts = [rel_counts[r] for r in rels]
    ax.barh(rels, rcounts, color="#e94560", edgecolor="#30363d")
    ax.set_title("Edge relations", **text_kw, fontsize=13, pad=10)
    ax.set_xlabel("Count", **text_kw)
    ax.tick_params(axis='y', labelsize=10, colors="#e6edf3")
    ax.tick_params(axis='x', colors="#e6edf3")

    # 3. Mini NetworkX layout (structural overview)
    ax = axes[2]
    ax.set_title("Graph structure", **text_kw, fontsize=13, pad=10)
    ax.axis("off")

    # Collapse to type-level graph for readability
    type_graph = nx.DiGraph()
    for src, tgt, edata in G.edges(data=True):
        src_type = G.nodes[src].get("__class__") or G.nodes[src].get("type", "?")
        tgt_type = G.nodes[tgt].get("__class__") or G.nodes[tgt].get("type", "?")
        rel = _edge_label(edata) or "→"
        if not type_graph.has_edge(src_type, tgt_type):
            type_graph.add_edge(src_type, tgt_type, label=rel, count=0)
        type_graph[src_type][tgt_type]["count"] += 1

    pos = nx.spring_layout(type_graph, seed=42, k=2.5)
    node_colors_list = [_color(n) for n in type_graph.nodes()]
    nx.draw_networkx_nodes(type_graph, pos, ax=ax, node_color=node_colors_list,
                           node_size=1400, edgecolors="#ffffff", linewidths=1.5)
    nx.draw_networkx_labels(type_graph, pos, ax=ax,
                            font_color="#e6edf3", font_size=9)
    nx.draw_networkx_edges(type_graph, pos, ax=ax,
                           edge_color="#4a5568", arrows=True,
                           arrowsize=15, node_size=1400,
                           connectionstyle="arc3,rad=0.1")
    edge_labels = {(s, t): f"{d['label']}\n×{d['count']}"
                   for s, t, d in type_graph.edges(data=True)}
    nx.draw_networkx_edge_labels(type_graph, pos, edge_labels=edge_labels,
                                 ax=ax, font_size=7, font_color="#9ca3af")

    # Legend
    legend_handles = [
        mpatches.Patch(color=_color(t), label=t)
        for t in type_counts
    ]
    ax.legend(handles=legend_handles, loc="lower right", fontsize=8,
              facecolor="#161b22", edgecolor="#30363d",
              labelcolor="#e6edf3")

    plt.suptitle(
        f"Knowledge Graph  ·  {G.number_of_nodes()} nodes  ·  {G.number_of_edges()} edges",
        color="#e6edf3", fontsize=14, y=1.01,
    )
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight",
                facecolor="#0d1117")
    plt.close()
    print(f"Summary chart     → {out_path}")


# ── Main ───────────────────────────────────────────────────────────────────────

def _find_latest_graph() -> Path:
    test_output = Path("data/test_output")
    jsons = sorted(test_output.glob("*/docling_graph/graph.json"),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    if not jsons:
        raise FileNotFoundError("No graph.json found under data/test_output/")
    return jsons[0]


if __name__ == "__main__":
    if len(sys.argv) > 1:
        graph_path = Path(sys.argv[1])
    else:
        graph_path = _find_latest_graph()
        print(f"Using latest:  {graph_path}")

    G = load_graph(graph_path)
    print(f"Loaded graph:  {G.number_of_nodes()} nodes, {G.number_of_edges()} edges\n")

    out_dir = graph_path.parent
    make_interactive(G, out_dir / "graph_pretty.html")
    make_summary_chart(G, out_dir / "graph_summary.png")

    print("\nNode breakdown:")
    for t, n in Counter(
        d.get("__class__") or d.get("type", "?")
        for _, d in G.nodes(data=True)
    ).most_common():
        print(f"  {t:25s} {n}")

    print("\nExtracted segments:")
    for _, d in G.nodes(data=True):
        if (d.get("__class__") or d.get("type")) == "BusinessSegment":
            name = d.get("name") or "(unnamed)"
            rev = d.get("revenue") or "—"
            yoy = d.get("revenue_growth_yoy") or "—"
            print(f"  {name:30s}  {rev:10s}  {yoy} YoY")

    print("\nExtracted partners:")
    for nid, d in G.nodes(data=True):
        if (d.get("__class__") or d.get("type")) == "Partner":
            name = d.get("name") or _node_label(nid, d)
            dep = d.get("deployment") or "—"
            print(f"  {name:25s}  {dep[:60]}")

    print("\nTop financial metrics:")
    for _, d in G.nodes(data=True):
        if (d.get("__class__") or d.get("type")) == "FinancialMetric":
            if d.get("name") and d.get("value"):
                print(f"  {d['name']:40s}  {d['value']}")
