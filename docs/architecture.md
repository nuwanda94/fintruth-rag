# Architecture

Current shape of the interview-max system. Week 3 will expand this with
the LangGraph loop and Streamlit evidence panel.

```
SEC filings (edgartools) → parser (MD&A / risk / notes)
  → chunker (512 / 64 + metadata payload)
  → SQLite catalog + processed JSON
  → embedder (hash-local today; voyage/OpenAI hook)
  → VectorStore (in-memory today; Qdrant hook)
  → HybridRetriever (dense kNN + BM25 + RRF ± lexical rerank)
  → RetrievalFilters (ticker / form / section / as_of)
  → generate_answer (extractive default, optional Grok)
       ├ should_refuse gates
       ├ [n] citations + Sources footer
       └ REFUSAL: otherwise
  → eval runner (questions.jsonl → evals/results/*.json)
```

Default runtime is fully offline. Network is used only for EDGAR ingest
and optional `https://api.x.ai/v1/chat/completions`.

See `docs/design_decisions.md` for why each box exists and
`evals/failure_analysis.md` for known holes on the demo corpus.
