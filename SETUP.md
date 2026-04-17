# Setup Guide
## From PDFs to Knowledge Graphs — AMLC 2026

Complete this **before** the tutorial. Expected time: 20–30 min (mostly model download).

---

## What You Need

| Requirement | Notes |
|---|---|
| Python 3.11+ | Managed by `uv` — no manual install needed |
| [uv](https://docs.astral.sh/uv/) | Fast Python package + venv manager |
| [Ollama](https://ollama.com/download) | Runs local LLMs |
| `gemma4:e4b` model | ~10 GB download |
| 12 GB free disk space | Model + dependencies |

---

## Step 1 — Install uv

**Mac / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Restart your terminal after installing.

---

## Step 2 — Clone the repo and install dependencies

```bash
git clone https://github.com/KrishnaRekapalli/docling-graph-tutorial
cd docling-graph-tutorial
uv sync --python 3.11
```

This creates a `.venv` with Python 3.11 and installs all dependencies automatically.

---

## Step 3 — Install Ollama

Download and install from: **https://ollama.com/download**

- Mac: drag to Applications, launch the app
- Windows: run the installer, Ollama runs in the system tray
- Linux: `curl -fsSL https://ollama.com/install.sh | sh`

Verify the version (**0.20.7+ required** for gemma4:e4b):
```bash
ollama --version
```

If your version is older, download the latest from the link above before continuing.

---

## Step 4 — Download the model (~10 GB)

```bash
ollama pull gemma4:e4b
```

This takes 10–20 min depending on your connection. Start it now.

Once downloaded, create the 8k context variant (prevents prompt truncation):

```bash
ollama create gemma4-8k -f Modelfile-gemma4-8k
```

The `Modelfile-gemma4-8k` file is included in the repo root.

---

## Step 5 — (Optional) Remote API keys

If you have a remote API key you'd like to use alongside the local model:

```bash
cp .env.example .env
```

Edit `.env` and add whichever key you have — only one is needed:
```
OPENAI_API_KEY="..."        # OpenAI
MISTRAL_API_KEY="..."       # Mistral
GEMINI_API_KEY="..."        # Google Gemini

# IBM WatsonX
WATSONX_API_KEY="..."       # IBM WatsonX API Key
WATSONX_PROJECT_ID="..."    # IBM WatsonX Project ID
WATSONX_URL="..."           # IBM WatsonX URL (optional)
```

Remote models are **not required** — `gemma4-8k` runs fully locally.

---

## Step 6 — Verify everything

```bash
uv run python 00_setup_check.py
```

Expected output:
```
  ✓  Python 3.11
  ✓  Package: docling-graph
  ✓  Package: docling
  ...
  ✓  Ollama daemon running
  ✓  Ollama model: gemma4-8k
  ✓  Model pre-warmed (keep_alive=1h)

  ✓  All 14 checks passed — you're ready!
```

---

## Troubleshooting

**`uv` not found after install**
Restart your terminal. If still missing, add `~/.cargo/bin` (Mac/Linux) to your PATH.

**`ollama list` says command not found**
Ollama app isn't running. Open it from Applications (Mac) or system tray (Windows).

**`gemma4-8k` not found**
Run Step 4 again. Check `ollama list` to see what's downloaded.

**Corporate Windows — Ollama port blocked**
Ollama uses port 11434. If blocked, use a remote API key instead (Step 5).

**Intel Mac — model is very slow**
gemma4:e4b runs on CPU on Intel Macs (~5–10 min per run). Use the pre-run fallback:
```bash
uv run python load_prerun.py
```
Then open `01_quickstart.ipynb` — the graphs will already be loaded.

---

## If All Else Fails — Pre-run Fallback

If you can't get the model working, load pre-extracted graphs and follow along with the query and visualization sections:

```bash
uv run python load_prerun.py
```

This loads both the home insurance and NVIDIA graphs into `data/prerun/` so every notebook cell will work without running extraction.

---
