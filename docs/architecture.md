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
