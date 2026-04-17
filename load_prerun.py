"""
Pre-run fallback for the AMLC 2026 tutorial.

If extraction fails or you can't run Ollama, run this once:
    uv run python load_prerun.py

It copies pre-extracted graphs into data/prerun/ so every notebook
cell works without running the extraction pipeline.

Expected output:
    ✓  data/prerun/home_policy_graph.json  (14 nodes, 13 edges)
    ✓  data/prerun/earnings_graph.json     (N nodes, N edges)
"""

import json
import shutil
from pathlib import Path

PASS = "  ✓"
FAIL = "  ✗"

DATA_DIR   = Path(__file__).parent / "data"
PRERUN_DIR = DATA_DIR / "prerun"


def _verify_graph(path: Path) -> tuple[int, int]:
    """Return (nodes, edges) count for a graph JSON file."""
    with open(path) as f:
        data = json.load(f)
    return len(data.get("nodes", [])), len(data.get("edges", []))


def main():
    print("\n" + "─" * 55)
    print("  Pre-run Fallback Loader")
    print("─" * 55 + "\n")

    PRERUN_DIR.mkdir(parents=True, exist_ok=True)

    graphs = {
        "home_policy_graph.json": "Home insurance graph (01_concepts.ipynb)",
        "earnings_graph.json":    "NVIDIA earnings graph (02_schema.ipynb)",
    }

    all_ok = True
    for filename, desc in graphs.items():
        dest = PRERUN_DIR / filename

        if dest.exists():
            try:
                nodes, edges = _verify_graph(dest)
                print(f"{PASS}  {filename}  ({nodes} nodes, {edges} edges)")
            except Exception as e:
                print(f"{FAIL}  {filename}  — corrupted: {e}")
                all_ok = False
        else:
            # Check if there's a freshly generated graph we can copy in
            candidates = list(DATA_DIR.glob(f"**/{filename}"))
            candidates = [c for c in candidates if "prerun" not in str(c)]
            candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)

            if candidates:
                shutil.copy2(candidates[0], dest)
                nodes, edges = _verify_graph(dest)
                print(f"{PASS}  {filename}  — copied from {candidates[0].parent.name}  ({nodes} nodes, {edges} edges)")
            else:
                print(f"{FAIL}  {filename}  — not found")
                print(f"       Run extraction first: see SETUP.md for instructions")
                all_ok = False

    print()
    if all_ok:
        print("  All pre-run graphs ready.")
        print("  Open notebooks/01_concepts.ipynb — extraction cells will load these automatically.\n")
    else:
        print("  Some graphs are missing. Run the extraction scripts first:")
        print("    uv run python extract_home_policy.py")
        print("    uv run python extract_earnings.py")
        print("  Then re-run this script.\n")

    print("─" * 55 + "\n")


if __name__ == "__main__":
    main()
