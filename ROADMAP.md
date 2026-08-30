# FinTruth RAG — Interview-Max Roadmap

**SEC-Grounded Financial Research Assistant**  
High-Signal Project for xAI / Grok Interview  
Owner: nuwanda94 | Repo: https://github.com/nuwanda94/fintruth-rag

## 1. Goal & Success Criteria

Ship a focused, deeply understood, measurable system that demonstrates strong retrieval engineering (hybrid + metadata/temporal), truth-seeking behavior (grounding, citations, refusal), serious evaluation + failure analysis, and the ability to defend every major design decision with data or first principles.

**Done when you can:**
1. Explain the problem and scope choices
2. Walk through architecture and justify each major component
3. Show live easy + hard queries with evidence
4. Present ablation results and residual failures
5. Discuss trade-offs and what you would do with more time / scale
6. Answer deep questions about retrieval, chunking, filtering, and evaluation

## 2. Strict Scope

### IN (Must ship and own deeply)
- Corpus: 8–12 large-cap companies, 3–5 years of 10-K + 10-Q filings
- High-quality section-aware ingestion (MD&A + Risk Factors + key notes)
- Hybrid retrieval (dense + sparse) + metadata/temporal filtering + reranker
- Strictly grounded generation with citations and explicit refusal / low-confidence path
- Serious evaluation harness (30–50 hard questions) with ablations and failure analysis
- Clean evidence-showing demo (Streamlit)
- Clear design-decision log and known limitations

### OUT (Explicitly deferred)
- Full agentic multi-hop graphs and complex tool use (minimal retrieve → grade → generate → refuse only)
- Advanced parent-document / contextual retrieval (only if time remains)
- Heavy multi-modal table understanding or full XBRL fact extraction
- Conflict detection across entire corpus, production multi-tenancy, Docker polish, real-time news/X

## 3. Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Language / Env | Python 3.11+ / uv | Modern, fast |
| Orchestration | LangChain + minimal LangGraph | Retrieval + simple agent loop |
| Vector + Hybrid | Qdrant | Native hybrid + strong metadata filters |
| Embeddings | voyage-finance-2 or text-embedding-3-large / BGE | Finance performance |
| Reranker | Cohere Rerank or BGE-reranker | Precision lift |
| LLM | xAI Grok API (primary) + cheap fallback | Alignment signal + cost |
| Ingestion | edgartools + BeautifulSoup/lxml | Best SEC handling |
| Evaluation | RAGAS + custom numerical/citation | Standard + domain metrics |
| UI / Observability | Streamlit + LangSmith/Langfuse | Fast evidence panel + traces |

## 4. File Structure

```
fintruth-rag/
├── README.md, pyproject.toml, .env.example, Makefile, PROGRESS.md, ROADMAP.md
├── data/{raw, processed, catalog.db}
├── src/fintruth/
│   ├── config.py
│   ├── ingestion/   (downloader.py, parser.py, chunker.py, pipeline.py)
│   ├── indexing/    (embedder.py, qdrant_store.py)
│   ├── retrieval/   (hybrid.py, filters.py, reranker.py)
│   ├── generation/  (prompts.py, chain.py)
│   ├── agent/       (graph.py)  # minimal only
│   ├── eval/        (dataset.py, metrics.py, runner.py)
│   └── ui/          (app.py)
├── scripts/         (ingest.py, index.py, run_eval.py, create_eval_set.py)
├── evals/           (questions.jsonl, results/, failure_analysis.md)
├── notebooks/
├── tests/
└── docs/            (architecture.md, design_decisions.md, limitations.md, exceptional_work.md)
```

## 5. Week-by-Week Task List

### WEEK 1 — Foundation + Working End-to-End Loop

**Days 1–2: Setup & Ingestion**
- chore: Initialize repo, uv + pyproject.toml, config, logging, full folder structure
- feat: SEC downloader (edgartools) for 8–12 companies (10-K + 10-Q)
- feat: Section-aware parser (MD&A + Risk Factors) + chunker + metadata schema
- chore: Local catalog (SQLite) + processed storage → scripts/ingest.py works

**Days 3–4: Indexing + Core Retrieval**
- feat: Embedding + Qdrant upsert with rich payload
- feat: Hybrid retriever (dense + sparse + RRF) + basic metadata filters
- feat: Grounded generation prompt + citation extraction
- Deliverable: CLI/notebook answers a question and shows source chunks

**Day 5: Thin Eval + Stabilization**
- feat: Start evals/questions.jsonl (15–20 questions) + minimal eval runner
- test: Smoke tests; docs: README with run instructions
- Deliverable: Working loop + first traces

### WEEK 2 — Quality Jump

**Days 1–2: Retrieval Hardening**
- feat: Add reranker; improve temporal & section filters; refine chunking from failures
- perf: Latency/token tracking
- Deliverable: naive vs hybrid vs +rerank comparison

**Days 3–4: Generation & Refusal**
- feat: Stronger grounding + explicit refusal path + citation formatting
- feat: Expand eval set to 30–40 hard questions
- test: Full eval + results
- Deliverable: First real ablation numbers + failure examples

**Day 5: Analysis & Iteration**
- docs: design_decisions.md + failure_analysis.md
- fix: Top failure modes
- Deliverable: Clear before/after metrics and documented decisions

### WEEK 3 — Depth, Demo & Interview Packaging

**Days 1–2: Minimal Truth-Seeking + Demo**
- feat: Minimal LangGraph loop (retrieve → grade → generate or refuse)
- feat: Streamlit UI (answer + expandable chunks/scores/metadata + citations + refusal indicator)
- Deliverable: Shareable demo

**Days 3–4: Evaluation Depth & Docs**
- feat: Custom numerical + citation accuracy checks; final ablation suite
- docs: Complete design_decisions, limitations, architecture, exceptional_work one-pager, polished README
- Deliverable: Full package ready for walkthrough

**Day 5: Rehearsal & Buffer**
- Live practice of 10–15 min walkthrough
- Fix sharp edges; final failure analysis; tag clean release

## 6. Iteration Logging Convention

Every automated (or human) run **must** update `PROGRESS.md` at the repo root with:

- Iteration number / timestamp
- What was completed in this run (specific files, commits, features)
- Current status against the roadmap (which Week/Day tasks are done)
- What to pick up in the next iteration (exact next tasks)
- Blockers or decisions needed
- Latest eval metrics if any

This ROADMAP.md is the single source of truth. All work must follow it strictly.
