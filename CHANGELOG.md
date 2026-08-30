# Changelog

Packaging notes for interview-max FinTruth RAG. Git tag `v0.1.0` is optional
(create-tag is not in the connected GitHub tool set); this file is the source
of truth for what that tag should mean.

## 0.1.0 — 2026-08-30

Interview-max offline package.

### In scope, shipped
- Section-aware ingest scaffold (edgartools + MD&A / Risk Factors chunker + SQLite catalog)
- Hybrid retrieve (dense + sparse + RRF) with metadata / as-of filters and lexical rerank
- Extractive grounded generation with citations and issuer-aware refusal
- Minimal retrieve → grade → generate|refuse graph + Streamlit evidence UI
- Seeded eval harness (n=34) with refusal / citation / keyword / numerical contract metrics
- Retrieval ablation helper (dense vs hybrid vs +rerank) on the demo fixture
- Interview docs: architecture, design decisions, limitations, exceptional work, walkthrough
- Live-ingest preflight (`scripts/ingest.py --preflight`) before hitting EDGAR

### Explicitly not in this tag
- Live EDGAR catalog numbers, voyage/Cohere quality embeddings, RAGAS
- GitHub Release / annotated tag (create locally: `git tag -a v0.1.0 -m "interview-max offline"`)
- Docker, multi-hop tools, XBRL, parent-document retrieval

### Demo snapshot (not IR quality)
See `evals/results/latest.json`. Residual miss: `q030`.
