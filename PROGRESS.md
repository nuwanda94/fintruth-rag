# FinTruth RAG — Progress Log

This file is the running log of automated and manual iterations.  
Every run must append a new entry at the top (most recent first).

---

## Iteration 3 — 2026-08-30 15:00 IST

**Completed**
- Finished Week 1 Days 3–4 grounded generation increment (offline-first):
  - `src/fintruth/generation/prompts.py` — system prompt, numbered evidence blocks, chat messages
  - `src/fintruth/generation/chain.py` — `GroundedAnswer`, `[n]` citation parse, score/overlap refusal, extractive fallback, LLM-text adapter
  - `scripts/ask.py` — question → hybrid retrieve → cited extractive answer (catalog or `--demo` fixture)
  - `tests/test_generation.py` — citation mapping, refusal, extractive cites, retrieve→generate smoke
- Makefile `ask` target; `generation/__init__.py` exports

**Current Status**
- Week 1 Days 1–2: ingestion pipeline implemented (not live-run against SEC)
- Week 1 Days 3–4: embed + hybrid retrieve + grounded prompt/citation/refusal **implemented and tested offline**; live Grok completion not wired yet
- Week 1 Day 5: eval set + README run instructions **not started**

**Next Iteration Should Pick Up**
1. Week 1 Day 5: seed `evals/questions.jsonl` with 15–20 hard questions + minimal `src/fintruth/eval/runner.py`
2. docs: README run instructions (`ingest` / `index` / `ask` / `pytest`)
3. Optional: call xAI Grok from `generate_answer` when `XAI_API_KEY` is set
4. Smoke live ingest when `SEC_USER_AGENT` + network are available

**Blockers / Notes**
- Extractive mode is the default so the loop works without LLM keys
- Hash embedder still used; replace before real eval quality claims
- Live ingest still needs a valid `SEC_USER_AGENT` and EDGAR access
- No eval metrics yet

**Eval metrics**
- n/a

---

## Iteration 2 — 2026-08-30 14:01 IST

**Completed**
- Started Week 1 Days 3–4 indexing + core retrieval (working increment, no live APIs required):
  - `src/fintruth/indexing/embedder.py` — `HashEmbedder` + `build_embedder` factory (deterministic offline default)
  - `src/fintruth/indexing/qdrant_store.py` — `InMemoryVectorStore`, optional `QdrantVectorStore`, `index_payloads`
  - `src/fintruth/retrieval/filters.py` — ticker / form / section / date-range filters
  - `src/fintruth/retrieval/hybrid.py` — sparse BM25-ish index + dense kNN + Reciprocal Rank Fusion
  - `src/fintruth/ingestion/catalog.py` — `iter_chunk_payloads()` for the indexer
  - `scripts/index.py` — CLI that reads the SQLite catalog and upserts embeddings
  - `tests/test_hybrid_retrieval.py` — offline smoke tests (deterministic embed + ticker/section filters)
- Config: `embedding_model=hash-local`, `embedding_dim`, `qdrant_in_memory`, retrieve_k knobs
- `qdrant-client` added to core deps; Makefile `index` target

**Current Status**
- Week 1 Days 1–2: ingestion pipeline implemented (still not live-run against SEC)
- Week 1 Days 3–4: embed + store + hybrid retrieve **skeleton implemented and tested offline**; grounded generation prompt + citation extraction **not started**

**Next Iteration Should Pick Up**
1. `src/fintruth/generation/prompts.py` + `generation/chain.py` — grounded answer prompt, citation parse, refusal stub
2. Tiny CLI or notebook: question → hybrid retrieve → print chunks (and later LLM answer)
3. Optional: Voyage/OpenAI embedder path behind the existing factory when keys exist
4. Harden parser on a real 10-K heading variants when live ingest is available

**Blockers / Notes**
- Live ingest still needs a valid `SEC_USER_AGENT` and network to EDGAR
- Default embedder is hash-local (fine for wiring tests; replace before real eval)
- Qdrant server is optional (`QDRANT_IN_MEMORY=true` uses `:memory:`)
- No eval metrics yet

**Eval metrics**
- n/a

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
