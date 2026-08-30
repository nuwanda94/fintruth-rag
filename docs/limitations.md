# Known Limitations

Interview-max scope only. See ROADMAP.md §2 OUT list. These are the constraints an interviewer should hear first — not after a live demo surprise.

## Corpus and ingestion

- Default path is `DEMO_CORPUS` (13 short fixture chunks). Live 8–12 issuer × 3–5 year 10-K/10-Q ingest still requires `SEC_USER_AGENT` and a writable catalog.
- Parser is section-aware for MD&A and Risk Factors only. Notes, financial statements, and XBRL facts are out of scope; `notes_sparse` eval items are expected refusals.
- Chunking is paragraph/section windows, not parent-document or contextual compression.

## Retrieval and embeddings

- Offline embedder is a **hash embedder**. Dense ranks on the demo fixture are not quality claims. Hybrid lift on demo data is mostly lexical (BM25 + RRF + lexical rerank).
- Qdrant is the intended production store; tests and `make eval --demo` use `InMemoryVectorStore`.
- Temporal `as_of` filtering exists but the demo filings are a single year, so cutoff behavior is only unit-tested, not measured on a real time series.
- Reranker offline is lexical overlap, not Cohere / BGE-reranker.

## Generation and agents

- Default generator is extractive: it quotes overlapping snippets with `[n]` citations. It does not synthesize across tables or reconcile conflicting years.
- Grok is optional (`XAI_API_KEY`). Eval **always** forces `use_llm=False` so scores stay deterministic.
- `TruthSeekingGraph` is retrieve → grade → generate|refuse. No multi-hop tools, no web/X, no conflict graph across the full corpus.
- Citation identity is 1-indexed retrieval order, not a stable document address in EDGAR.

## Evaluation

- Metrics are binary contract checks (refusal agreement, citation presence, citation ticker support, keyword coverage, ticker hit, optional gold numbers). They are **not** RAGAS faithfulness / answer-relevancy and must not be presented as such.
- Numerical checks fire when `expected_numbers` is set, or when the item is `numerical_absent` / `expect_refuse`. Scale-aware tokens (`201 billion`) must match magnitude; bare `201` still matches any scale. Synonyms like "handsets shipped" are not modeled.
- Ablation rates compare keyword-in-top-k across dense / hybrid / hybrid+rerank on the **same demo corpus**. Do not treat arm deltas as production IR quality.
- `evals/results/latest.json` is a checked-in **demo-corpus** snapshot (n=34). Live-catalog numbers still require ingest credentials.

## Demo UX

- Streamlit talks to the in-process graph + demo corpus unless a catalog is present. Filters are ticker / section / as-of, not full EDGAR search.
- Streamlit shows retrieve-pool latency and end-to-end graph latency. Token accounting is still deferred (extractive default has no LLM tokens).
