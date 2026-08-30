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

## Grade gates (`should_refuse` + post-cite checks)

Generation is blocked when any of these fire:

1. No retrieved chunks
2. Named issuer missing from hit payloads (ticker or company name)
3. Top fused score below `DEFAULT_MIN_SCORE`
4. No term overlap between question and chunk text
5. Exact-figure question ("exact" / "unit volume" / "units" / "deliveries") names a year that does **not** appear in chunk text (filing_date alone is not enough)
6. Multi-ticker question whose citations omit a named issuer (extractive selection covers issuers first; LLM answers that cite only one side are refused)

Eval scoring is separate from generation gates. Keyword checks read the
answer plus **cited** chunk text only; multi-ticker items with two or more
gold keywords require every keyword (AND) so an uncited neighbor cannot
complete a contrast. Comparison items may also set `keywords_by_ticker`:
each needle must appear in that issuer's cited spans (AAPL "revenue"
cannot score the MSFT side of q013).

Cited evidence is resolved by `Citation.chunk_id` first (`resolve_cited_chunk`).
The `[n]` marker is still a 1-based retrieve-list index for the model; after
rerank the eval harness must not treat that index as identity.

Gate 5 is why `q016` / `q030` refuse instead of quoting FY2024 iPhone revenue.
Gate 6 is why a comparison cannot quote only AAPL when the question also names MSFT.

## Default data path

`scripts/run_eval.py --demo` and Streamlit use `DEMO_CORPUS` (13 fixture chunks) until the SQLite catalog has rows. Live EDGAR is gated by `scripts/ingest.py --preflight`.
