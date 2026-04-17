# From PDFs to Knowledge Graphs

Hands-on tutorial for [AMLC 2026](https://appliedml.us/2026/).  
Build a knowledge graph from any PDF — using [docling-graph](https://github.com/docling-project/docling-graph), a Pydantic schema, and a local or remote LLM.

No graph databases. No vector stores. Just Python.

---

## What You'll Build

A pipeline that turns a PDF into a queryable NetworkX knowledge graph:

```
PDF  →  docling (parse)  →  LLM (extract)  →  graph (traverse)
```

We start with a home insurance declarations page and ask:  
*"List all coverages and their limits."*  
Then we show the same question answered by RAG — and why the graph wins.

---

## Setup

→ **[SETUP.md](SETUP.md)** — complete instructions including Ollama, model download, API key config, and verification.

---

## Setup Failed?

If Ollama isn't working or the model download is too slow:

```bash
uv run python load_prerun.py
```

This loads pre-extracted graphs into `data/prerun/` so every notebook cell works without running extraction. You can follow along with the query and visualization sections.

---

## Built With

- [docling-graph](https://github.com/docling-project/docling-graph) — PDF to knowledge graph pipeline
- [docling](https://github.com/docling-project/docling) — PDF parsing and OCR
- [NetworkX](https://networkx.org) — graph structure and traversal
- [sentence-transformers](https://www.sbert.net) — embeddings for the RAG comparison
