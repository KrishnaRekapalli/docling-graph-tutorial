"""
Shared graph utilities: terminal tree preview + post-extraction visualisation prompt.

Used by test_extraction.py, test_insurance.py, and any future extraction scripts.
"""

import subprocess
import sys

from pathlib import Path

import networkx as nx


# ── Terminal tree ─────────────────────────────────────────────────────────────

# Tree drawing characters
_PIPE   = "│   "
_TEE    = "├── "
_LAST   = "└── "
_BLANK  = "    "


def _best_label(node_id: str, data: dict) -> str:
    cls = data.get("__class__") or data.get("type", "")
    candidates = [
        data.get("name"),
        data.get("insured_name"),
        data.get("company"),
        data.get("fiscal_period"),
        data.get("invoice_number"),
        data.get("coverage_type"),
        data.get("policy_number"),
    ]
    name = next((c for c in candidates if c and str(c).strip()), None)

    # Append key value for metric/limit nodes
    value = data.get("value") or data.get("revenue") or data.get("amount")

    parts = []
    if cls:
        parts.append(f"[{cls}]")
    if name:
        parts.append(name)
    if value and value not in (name or ""):
        parts.append(f"→ {value}")

    return " ".join(parts) if parts else node_id.rsplit("_", 1)[0]


def _edge_label(G: nx.DiGraph, src: str, tgt: str) -> str:
    data = G.edges[src, tgt]
    rel = data.get("relation") or data.get("label") or ""
    mapping = {
        "key_metrics":      "METRIC",
        "segments":         "SEGMENT",
        "partners":         "PARTNER",
        "products":         "PRODUCT",
        "coverages":        "COVERAGE",
        "insurers":         "INSURER",
        "producer":         "PRODUCER",
        "insured":          "INSURED",
        "limits":           "LIMIT",
        "line_items":       "LINE_ITEM",
        "risk_factors":     "RISK",
        "key_products":     "PRODUCT",
    }
    return mapping.get(rel, rel.upper() if rel else "→")


def _find_roots(G: nx.DiGraph) -> list[str]:
    """Nodes with no incoming edges — document root(s)."""
    roots = [n for n in G.nodes() if G.in_degree(n) == 0]
    if not roots:
        # Fallback: highest out-degree node
        roots = [max(G.nodes(), key=lambda n: G.out_degree(n))]
    return roots



def print_graph_tree(G: nx.DiGraph) -> None:
    """Print an ASCII tree of the graph rooted at document root(s)."""
    from collections import Counter

    type_counts = Counter(
        d.get("__class__") or d.get("type", "?")
        for _, d in G.nodes(data=True)
    )

    print(f"\n{'─'*60}")
    print(f"  Graph tree  ({G.number_of_nodes()} nodes · {G.number_of_edges()} edges)")
    print(f"{'─'*60}")

    roots = _find_roots(G)
    visited: set[str] = set()

    for root in roots:
        label = _best_label(root, G.nodes[root])
        print(f"\n{label}")
        children = list(G.successors(root))
        visited.add(root)

        for i, child in enumerate(children):
            is_last = (i == len(children) - 1)
            edge_rel = _edge_label(G, root, child)
            child_label = _best_label(child, G.nodes[child])
            connector = _LAST if is_last else _TEE
            print(f"{connector}{edge_rel}  {child_label}")

            grandchildren = list(G.successors(child))
            g_prefix = _BLANK if is_last else _PIPE
            if child not in visited:
                visited.add(child)
                for j, gc in enumerate(grandchildren):
                    gc_is_last = (j == len(grandchildren) - 1)
                    gc_connector = _LAST if gc_is_last else _TEE
                    gc_edge = _edge_label(G, child, gc)
                    gc_label = _best_label(gc, G.nodes[gc])
                    print(f"{g_prefix}{gc_connector}{gc_edge}  {gc_label}")
                    # One more level
                    gg_prefix = g_prefix + (_BLANK if gc_is_last else _PIPE)
                    if gc not in visited:
                        gg_children = list(G.successors(gc))
                        visited.add(gc)
                        for k, ggc in enumerate(gg_children):
                            ggc_is_last = (k == len(gg_children) - 1)
                            ggc_connector = _LAST if ggc_is_last else _TEE
                            ggc_edge = _edge_label(G, gc, ggc)
                            ggc_label = _best_label(ggc, G.nodes[ggc])
                            print(f"{gg_prefix}{ggc_connector}{ggc_edge}  {ggc_label}")

    print(f"\n  Node types: " + " · ".join(f"{t}×{n}" for t, n in type_counts.most_common()))
    print(f"{'─'*60}")


# ── Post-extraction visualisation prompt ──────────────────────────────────────

def prompt_visualize(G: nx.DiGraph, out_dir: Path) -> None:
    """
    Ask the user if they want a pretty graph after extraction.
    Offers three options:
      1. Interactive HTML (our pyvis visualizer)
      2. docling-graph inspect (Cytoscape, opens in browser)
      3. Skip
    """
    graph_json = out_dir / "graph.json"
    if not graph_json.exists():
        return

    print("\nGenerate pretty graph?")
    print("  [1] Interactive HTML  (pyvis, dark theme)")
    print("  [2] docling-graph inspect  (Cytoscape, opens browser)")
    print("  [3] Skip")

    try:
        choice = input("Choice [1/2/3]: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    if choice == "1":
        _generate_pyvis(G, out_dir)
    elif choice == "2":
        _run_inspect(out_dir)
    else:
        print("Skipped.")


def _generate_pyvis(G: nx.DiGraph, out_dir: Path) -> None:
    try:
        import visualize_graph as vg
        out_path = out_dir / "graph_pretty.html"
        vg.make_interactive(G, out_path)
        vg.make_summary_chart(G, out_dir / "graph_summary.png")
        print(f"\nOpen in browser: {out_path.resolve()}")
    except Exception as e:
        print(f"Visualisation error: {e}")


def _run_inspect(out_dir: Path) -> None:
    """Use docling-graph's built-in Cytoscape visualiser."""
    try:
        subprocess.run(
            ["uv", "run", "docling-graph", "inspect", str(out_dir)],
            check=True,
        )
    except Exception as e:
        print(f"docling-graph inspect error: {e}")
        print(f"Run manually: uv run docling-graph inspect {out_dir}")
