"""
Setup verification for the AMLC 2026 tutorial:
  "From PDFs to Knowledge Graphs"

Run this before the tutorial:
    uv run python 00_setup_check.py

All checks must be green before starting 01_quickstart.ipynb.
If you're stuck, run: uv run python load_prerun.py
"""

import sys
import json
import os
import urllib.request
from pathlib import Path

PASS = "  ✓"
FAIL = "  ✗"
WARN = "  ⚠"

results = []
model_names = []

def check(label: str, ok: bool, detail: str = "") -> bool:
    icon = PASS if ok else FAIL
    msg = f"{icon}  {label}"
    if detail and not ok:
        msg += f"\n       {detail}"
    print(msg)
    results.append(ok)
    return ok


print("\n" + "─" * 55)
print("  Setup Check — From PDFs to Knowledge Graphs")
print("─" * 55 + "\n")


# ── Python version ────────────────────────────────────────────────────────────
v = sys.version_info
check(
    f"Python {v.major}.{v.minor}",
    v.major == 3 and v.minor >= 11,
    "" if v.major == 3 and v.minor >= 11 else "Need Python 3.11+. Use: uv python install 3.11"
)


# ── Core packages ─────────────────────────────────────────────────────────────
for pkg, import_name in [
    ("docling-graph",         "docling_graph"),
    ("docling",               "docling"),
    ("networkx",              "networkx"),
    ("pydantic",              "pydantic"),
    ("sentence-transformers", "sentence_transformers"),
    ("pyvis",                 "pyvis"),
    ("matplotlib",            "matplotlib"),
]:
    try:
        __import__(import_name)
        check(f"Package: {pkg}", True)
    except ImportError:
        check(f"Package: {pkg}", False, "Run: uv sync")


# ── Data files ────────────────────────────────────────────────────────────────
data_files = {
    "data/sample-declarations-page.pdf": "Home insurance demo document",
    "data/NVIDIAAn.pdf":                 "NVIDIA earnings document",
}
for path, desc in data_files.items():
    p = Path(path)
    check(f"Data file: {p.name}", p.exists(), f"Missing: {path}  ({desc})")


# ── Pre-run fallback graphs ───────────────────────────────────────────────────
print()
prerun_files = {
    "data/prerun/home_policy_graph.json": "Pre-extracted home insurance graph",
    "data/prerun/earnings_graph.json":    "Pre-extracted NVIDIA earnings graph",
}
for path, desc in prerun_files.items():
    p = Path(path)
    if p.exists():
        check(f"Pre-run: {p.name}", True)
    else:
        print(f"{WARN}  Pre-run: {p.name} — not found (run load_prerun.py if extraction fails)")


# ── Ollama daemon + version ───────────────────────────────────────────────────
print()
ollama_running = False
try:
    req = urllib.request.Request("http://localhost:11434/api/tags")
    with urllib.request.urlopen(req, timeout=3) as resp:
        ollama_running = resp.status == 200
        tags = json.loads(resp.read())
        model_names = [m["name"] for m in tags.get("models", [])]
    check("Ollama daemon running", True)
except Exception:
    check("Ollama daemon running", False,
          "Start Ollama: open the Ollama app or run 'ollama serve'")

if ollama_running:
    try:
        req = urllib.request.Request("http://localhost:11434/api/version")
        with urllib.request.urlopen(req, timeout=3) as resp:
            version_str = json.loads(resp.read()).get("version", "0.0.0")
        parts = [int(x) for x in version_str.split(".")[:3]]
        while len(parts) < 3:
            parts.append(0)
        version_ok = parts >= [0, 20, 7]
        check(
            f"Ollama version {version_str} (>=0.20.7 required)",
            version_ok,
            "Update Ollama: https://ollama.com/download" if not version_ok else "",
        )
    except Exception:
        check("Ollama version check", False, "Could not read version from Ollama API")


# ── gemma4-8k model ───────────────────────────────────────────────────────────
if ollama_running:
    has_gemma4 = any("gemma4-8k" in n for n in model_names)
    check(
        "Ollama model: gemma4-8k",
        has_gemma4,
        "" if has_gemma4 else (
            "Run:\n"
            "       ollama pull gemma4:e4b\n"
            "       ollama create gemma4-8k -f Modelfile-gemma4-8k"
        )
    )

    # ── Pre-warm model ────────────────────────────────────────────────────────
    if has_gemma4:
        print(f"  …  Pre-warming gemma4-8k (keeps model in memory for 1h)...", end="", flush=True)
        try:
            payload = json.dumps({
                "model": "gemma4-8k",
                "prompt": "hi",
                "stream": False,
                "keep_alive": "1h"
            }).encode()
            req = urllib.request.Request(
                "http://localhost:11434/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                warmup_ok = resp.status == 200
            print(" done" if warmup_ok else " failed")
            check("Model pre-warmed (keep_alive=1h)", warmup_ok)
        except Exception as e:
            print()
            check("Model pre-warmed", False, f"{e}")
else:
    check("Ollama model: gemma4-8k", False, "Cannot reach Ollama — fix daemon first")


# ── Optional: remote API keys ─────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

print()
print("  Optional remote providers (not required):")
for name, env_key in [
    ("OpenAI",   "OPENAI_API_KEY"),
    ("Mistral",  "MISTRAL_API_KEY"),
    ("Gemini",   "GEMINI_API_KEY"),
    ("WatsonX",  "WATSONX_API_KEY"),
]:
    val = os.getenv(env_key, "")
    if val:
        print(f"{PASS}  {name} API key found  (LLM_PROVIDER={name.lower()})")
    else:
        print(f"       {name}: not configured")


# ── Summary ───────────────────────────────────────────────────────────────────
print()
print("─" * 55)
passed = sum(results)
total  = len(results)

if passed == total:
    print(f"  ✓  All {total} checks passed — you're ready!\n")
    print("  Next: open notebooks/01_quickstart.ipynb\n")
else:
    failed = total - passed
    print(f"  {failed} check(s) failed out of {total}.\n")
    print("  Fix the issues above, then re-run this script.")
    print("  Stuck? Run:  uv run python load_prerun.py\n")

print("─" * 55 + "\n")
