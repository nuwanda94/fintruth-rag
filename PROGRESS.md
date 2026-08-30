# FinTruth RAG — Progress Log

This file is the running log of automated and manual iterations.  
Every run must append a new entry at the top (most recent first).

---

## Iteration 1 — 2026-08-30 13:20 IST

**Completed**
- Scaffolded interview-max tree: `src/fintruth/{config,logging,ingestion,indexing,retrieval,generation,agent,eval,ui}`, `scripts/`, `data/{raw,processed}`, `evals/`, `docs/`, `tests/`, `notebooks/`
- Added `pyproject.toml` (uv/hatch, pydantic-settings, edgartools, bs4/lxml, tiktoken), `.env.example`, `.gitignore`, `Makefile`
- Implemented working ingestion increment (not stubs-only):
  - `src/fintruth/config.py` — Settings + default 10-ticker universe
  - `src/fintruth/ingestion/downloader.py` — edgartools 10-K/10-Q fetch + disk cache
  - `src/fintruth/ingestion/parser.py` — MD&A / Risk Factors / notes HTML sections
  - `src/fintruth/ingestion/chunker.py` — token windows + Qdrant-ready payload
  - `src/fintruth/ingestion/catalog.py` — SQLite filings/chunks
  - `src/fintruth/ingestion/pipeline.py` + `scripts/ingest.py` CLI
- Smoke tests: `tests/test_chunker.py` (parse + chunk metadata, no network)

**Current Status**
- Week 1 Days 1–2: structure + config + ingestion pipeline **implemented**; not yet run against live SEC (needs `uv sync` + `SEC_USER_AGENT`)
- Week 1 Days 3–4 (embed/Qdrant/hybrid/generation) not started

**Next Iteration Should Pick Up**
1. `uv sync` locally and smoke `python scripts/ingest.py --tickers AAPL --years 1` (verify catalog + processed JSONL)
2. Harden parser on a real 10-K (item heading variants, 10-Q Item 2 MD&A)
3. Start Days 3–4: `indexing/embedder.py` + `indexing/qdrant_store.py`
4. Hybrid retriever skeleton (`retrieval/hybrid.py`, `retrieval/filters.py`)

**Blockers / Notes**
- Live ingest needs a valid SEC User-Agent email in `.env` (`SEC_USER_AGENT`)
- edgartools API surface can drift; downloader already degrades per-ticker
- No eval metrics yet

**Eval metrics**
- n/a

---

## Iteration 0 — Bootstrap (2026-08-30)

**Completed**
- Created GitHub repository: https://github.com/nuwanda94/fintruth-rag
- Added README.md with project overview, scope, stack, and structure
- Added ROADMAP.md (full interview-max week-by-week plan — single source of truth)
- Initialized this PROGRESS.md

**Current Status**
- Week 1, Day 1 not yet started
- Repo exists and is empty of code (structure and docs only)

**Next Iteration Should Pick Up**
1. Create full folder structure under `src/`, `scripts/`, `data/`, `evals/`, `docs/`, `tests/`, `notebooks/`
2. Add `pyproject.toml` with core dependencies (uv-compatible)
3. Add `.env.example`, `Makefile`, basic `src/fintruth/config.py`
4. Implement skeleton for ingestion (downloader.py, parser.py, chunker.py)
5. Commit as: `chore: scaffold project structure and config`

**Blockers / Notes**
- None. Ready for first code iteration.
- Automation should follow ROADMAP.md strictly and always update this file.
