# FinTruth RAG

**SEC-Grounded Financial Research Assistant**  
High-signal RAG project optimized for an xAI / Grok interview deep-dive.

## Goal
Ship a focused, deeply understood, measurable system demonstrating:
- Strong retrieval engineering (hybrid + metadata/temporal filtering + reranker)
- Truth-seeking behavior (strict grounding, citations, explicit refusal)
- Serious evaluation + failure analysis
- Ability to defend every major design decision with data or first principles

## Strict Scope

### In
- 8–12 large-cap companies, 3–5 years of 10-K + 10-Q
- Section-aware ingestion (MD&A, Risk Factors, key notes)
- Hybrid retrieval + metadata/temporal filters + reranker
- Grounded generation with citations + refusal path
- Eval harness (30–50 hard questions) + ablations + failure analysis
- Clean Streamlit evidence-showing demo
- Design-decision log + limitations

### Out
- Complex multi-hop agentic graphs / heavy tools
- Full multi-modal table/XBRL extraction
- Production multi-tenancy, Docker polish, real-time news/X

## Tech Stack
- Python 3.11+ / uv
- LangChain + minimal LangGraph (optional extra; default graph is a typed state machine)
- Qdrant (hybrid + filtering)
- Embeddings: voyage-finance-2 or text-embedding-3-large / BGE (hash-local offline default)
- Reranker: Cohere or BGE-reranker (lexical stand-in offline)
- LLM: xAI Grok API (primary); extractive fallback without keys
- Ingestion: edgartools + BeautifulSoup/lxml
- Eval: custom refusal/citation/keyword checks (RAGAS later)
- UI: Streamlit | Observability: LangSmith / Langfuse

## Quick start (offline loop)

```bash
uv sync --extra dev
cp .env.example .env   # set SEC_USER_AGENT before live ingest

# unit + integration smoke (no network, no API keys)
uv run pytest -q
# or: make test

# retrieve → cited extractive answer on the built-in fixture
uv run python scripts/ask.py --demo "What competition risks does Apple disclose?"
# or: make ask

# seeded eval set against the demo corpus
uv run python scripts/run_eval.py --demo
# or: make eval
uv run python scripts/create_eval_set.py   # list items

# evidence UI (retrieve → grade → generate|refuse)
uv sync --extra ui
uv run --extra ui streamlit run src/fintruth/ui/app.py
# or: make ui
```

## Live corpus (needs `SEC_USER_AGENT` in `.env`)

```bash
uv run python scripts/ingest.py --tickers AAPL --years 1
# or: make ingest

uv run python scripts/index.py
# or: make index

uv run python scripts/ask.py "What competition risks does Apple disclose?" --ticker AAPL

# same eval harness, now over catalog chunks if present
uv run python scripts/run_eval.py
```

Results land in `evals/results/latest.json`. Metrics are refusal accuracy, citation presence, keyword coverage, and ticker hit-rate — not yet RAGAS / numerical extraction.

## File Structure
```
fintruth-rag/
├── README.md, pyproject.toml, .env.example, Makefile, PROGRESS.md
├── data/{raw, processed, catalog.db}
├── src/fintruth/{config.py, ingestion/, indexing/, retrieval/, generation/, agent/, eval/, ui/}
├── scripts/{ingest.py, index.py, ask.py, run_eval.py, create_eval_set.py}
├── evals/{questions.jsonl, results/, failure_analysis.md}
├── notebooks/, tests/
└── docs/{architecture.md, design_decisions.md, limitations.md, exceptional_work.md}
```

## Roadmap (Interview-Max)
See [ROADMAP.md](ROADMAP.md) for the full week-by-week plan.

**Week 1**: Foundation + working end-to-end loop  
**Week 2**: Quality jump (reranker, refusal, ablations)  
**Week 3**: Minimal truth-seeking loop + Streamlit demo + packaging

## Progress
See [PROGRESS.md](PROGRESS.md) for iteration logs (updated by automation and humans).

## License
MIT
