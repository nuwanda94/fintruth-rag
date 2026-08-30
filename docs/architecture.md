# Architecture

Offline-first pipeline matching the current modules:

```
SEC / demo fixture
    → ingestion (download → parse sections → chunk → SQLite catalog)
    → indexing (hash/API embedder → InMemoryVectorStore or Qdrant)
    → retrieval (dense kNN + sparse BM25 → RRF → lexical rerank + as_of filters)
    → agent graph (retrieve → grade → generate | refuse)
    → generation (extractive default; optional Grok + citation/refusal gates)
    → eval harness / Streamlit evidence UI / ask.py CLI
```

Week 3 loop is `TruthSeekingGraph` in `src/fintruth/agent/graph.py`. LangGraph is an optional compile of the same nodes; tests run the typed state machine with no extra deps.

## Grade gates (`should_refuse`)

Generation is blocked when any of these fire:

1. No retrieved chunks
2. Named issuer missing from hit payloads (ticker or company name)
3. Top fused score below `DEFAULT_MIN_SCORE`
4. No term overlap between question and chunk text
5. Exact-figure question ("exact" / "unit volume" / "units" / "deliveries") names a year that does **not** appear in chunk text (filing_date alone is not enough)

Gate 5 is why `q016` / `q030` refuse instead of quoting FY2024 iPhone revenue.

## Default data path

`scripts/run_eval.py --demo` and Streamlit use `DEMO_CORPUS` (13 fixture chunks) until the SQLite catalog has rows. Live EDGAR is gated by `scripts/ingest.py --preflight`.
