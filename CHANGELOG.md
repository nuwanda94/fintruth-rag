# Changelog

Packaging notes for interview-max FinTruth RAG. Git tag `v0.1.0` is optional
(create-tag is not in the connected GitHub tool set); this file is the source
of truth for what that tag should mean.

## 0.1.5 — 2026-08-31

Unit-aware numerical scoring and unit-volume refusal gate (F2 residual).

- `parse_quantity` / `extract_quantities` distinguish `$201 billion` from `201 million`
- `score_numerical` requires matching scale when gold tokens include one
- `should_refuse` blocks exact unit-volume asks that only have dollar figures
- Generation package split: `citations.py`, `refuse.py`, `units.py`, `generate.py`

## 0.1.4 — 2026-08-31

Eval citations resolve by stable `chunk_id` after retrieve-list reorder.

- `resolve_cited_chunk` prefers payload identity, then 1-based index
- Keyword / numerical / citation-support checks follow the same lookup
- Stale `chunk_id` not present in the current pool fails citation support
- Unit test: shuffled neighbor at index 1 cannot steal the cited span

## 0.1.3 — 2026-08-31

Per-issuer keyword alignment on comparison questions.

- `EvalQuestion.keywords_by_ticker` loaded from `evals/questions.jsonl`
- `score_keywords` requires each issuer's needles in that issuer's cited spans
- q013 / q025 / q032 gold maps: AAPL→iphone+revenue, MSFT→azure, META→regulatory,
  GOOGL→regulation, XOM→climate, UNH→medical

## 0.1.2 — 2026-08-31

Eval keyword metric no longer credits the uncited retrieve pool.

- `score_keywords` uses answer + cited chunk text only
- Multi-ticker items with ≥2 gold keywords require all of them (AND)
- Unit tests cover one-sided / uncited-pool false positives

## 0.1.1 — 2026-08-31

Offline sharp-edge on comparison questions.

- Extractive quote selection covers every named ticker before rank order
- Post-cite refuse when a multi-ticker answer omits an issuer from citations
- Eval `citation_support` / `ticker_hit_rate` require full issuer cover on `multi_ticker` items

## 0.1.0 — 2026-08-30

Interview-max offline package.

### In scope, shipped
- Section-aware ingest scaffold (edgartools + MD&A / Risk Factors chunker + SQLite catalog)
- Hybrid retrieve (dense + sparse + RRF) with metadata / as-of filters and lexical rerank
- Extractive grounded generation with citations and issuer-aware refusal
- Period gate: exact-figure questions refuse when the asked year is missing from chunk text (`q030`)
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
See `evals/results/latest.json`. `q030` is covered by the period gate (expected refuse).
