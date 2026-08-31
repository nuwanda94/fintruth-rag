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

`GraphRun` records retrieve ms, generate ms, end-to-end ms, and `TokenUsage`.
Extractive answers use a char/4 estimate; Grok responses keep provider `usage` when present.

## Grade gates (`should_refuse` + post-cite checks)

Generation is blocked when any of these fire:

1. No retrieved chunks
2. Named issuer missing from hit payloads (ticker or company name)
3. Top fused score below `DEFAULT_MIN_SCORE`
4. No term overlap between question and chunk text
5. Exact-figure question ("exact" / "unit volume" / "units" / "deliveries") names a year that does **not** appear in chunk text (filing_date alone is not enough)
6. Exact-figure question whose asked year is not within `YEAR_QUANTITY_WINDOW` of a real quantity (dollar, grouped thousands, or scaled count). A distant "2012" store-opening sentence next to FY2024 revenue is not period evidence.
7. Exact unit-volume question whose asked year is not within that window of a *unit* quantity (`UNIT_QUANTITY_RE`). FY2012 *revenue* plus FY2024 units is not unit-volume evidence for 2012.
8. Exact unit-volume question whose chunks have no number paired with units/deliveries/shipments (dollar revenue is not a substitute)
9. Exact-figure question that names a reporting segment (Greater China, Americas, Europe, Japan, Rest of Asia Pacific) whose asked year is not within that window of the segment phrase. Americas units in FY2012 are not Greater China evidence.
10. Multi-ticker question whose citations omit a named issuer (extractive selection covers issuers first; LLM answers that cite only one side are refused)

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
Gate 6 is why a year that only appears far from any figure still refuses.
Gate 7 is why a year sitting next to the *wrong* figure (dollars vs units) still refuses.
Gate 8 is why a FY2012 *revenue* sentence cannot answer a unit-volume ask.
Gate 9 is why a year next to the right *kind* of figure in the wrong geography still refuses.
Gate 10 is why a comparison cannot quote only AAPL when the question also names MSFT.
Eval gold numbers may include a scale (`201 billion` on q002).

## Default data path

`scripts/run_eval.py --demo` and Streamlit use `DEMO_CORPUS` (13 fixture chunks) until the SQLite catalog has rows. Live EDGAR is gated by `scripts/ingest.py --preflight`.
