# FinTruth RAG — Progress Log

This file is the running log of automated and manual iterations.  
Every run must append a new entry at the top (most recent first).

---

## Iteration 6 — 2026-08-30 18:02 IST

**Completed**
- Week 2 Days 3–4 generation / refusal / eval-set expansion (offline-first):
  - `src/fintruth/generation/chain.py` — `Sources:` citation footer, multi-ticker coverage refusal, LLM uncited-claim refusal, optional `complete_with_grok` when `XAI_API_KEY` is set
  - `src/fintruth/generation/prompts.py` — system prompt tells the model not to invent a Sources block
  - `evals/questions.jsonl` — 34 items (was 18); added multi-ticker, notes-sparse, numerical-absent, out-of-corpus refusals
  - `src/fintruth/eval/runner.py` — eval path forced extractive for deterministic scores
  - `scripts/ask.py` — `--extractive`; prints structured citation lines + mode
  - `tests/test_generation.py` / `tests/test_eval.py` — footer, uncited LLM refuse, multi-ticker miss, floor ≥ 30

**Current Status**
- Week 1: foundation + offline end-to-end loop + thin eval **done**
- Week 2 Days 1–2: reranker + as-of + ablation helper **done offline**
- Week 2 Days 3–4: stronger grounding/refusal + 34-question set **implemented offline**; live ablation numbers / RAGAS **not started**
- Week 2 Day 5 (design_decisions + failure_analysis from real failures) **not started**

**Next Iteration Should Pick Up**
1. Week 2 Day 5: first pass of `docs/design_decisions.md` + `evals/failure_analysis.md` from demo-eval failure modes
2. Persist `evals/results/` from `make eval` when a writable checkout is available
3. Smoke live ingest when `SEC_USER_AGENT` + EDGAR are available
4. Week 3 Days 1–2: minimal LangGraph retrieve → grade → generate/refuse + Streamlit evidence UI

**Blockers / Notes**
- Grok path uses stdlib `urllib` against `https://api.x.ai/v1/chat/completions`; eval harness never calls it
- Hash embedder still used; demo composite is a wiring score, not a quality claim
- Live catalog numbers still blocked on ingest credentials

**Eval metrics**
- Question bank n=34. Demo composite still expected > 0.5 in `tests/test_eval.py`. No live-catalog numbers.

---

## Iteration 5 — 2026-08-30 17:00 IST

**Completed**
- Week 2 Days 1–2 retrieval hardening (offline-first):
  - `src/fintruth/retrieval/reranker.py` — `LexicalReranker` (Jaccard + section hint + recency) + factory
  - `src/fintruth/retrieval/hybrid.py` — optional rerank pool, `mode=dense|sparse|hybrid`, `RetrieveTrace` latency
  - `src/fintruth/retrieval/filters.py` — `as_of` point-in-time cutoff (tightens `date_to`)
  - `src/fintruth/retrieval/compare.py` — naive dense vs hybrid vs hybrid+rerank arms
  - `tests/test_reranker.py` — rerank order, as-of drop of later filings, ablation smoke
  - `scripts/ask.py` — `--compare`, `--no-rerank`, `--as-of`; prints rerank scores + latency
  - Config / `.env.example`: `RERANKER_MODEL`, `RERANK_ENABLED`, `RERANK_POOL_K`
  - Makefile `compare` target

**Current Status**
- Week 1: foundation + offline end-to-end loop + thin eval **done** (not live-run against SEC)
- Week 2 Days 1–2: reranker + temporal as-of + ablation helper **implemented offline**
- Week 2 Days 3–4 (stronger generation/refusal, 30–40 questions, live ablation numbers) **not started**
- No Cohere/cross-encoder network call yet (lexical stand-in by design)

**Next Iteration Should Pick Up**
1. Week 2 Days 3–4: stronger grounding + explicit refusal path polish + citation formatting
2. Expand `evals/questions.jsonl` toward 30–40 hard items (keep demo-compatible golds)
3. Optional: call xAI Grok from `generate_answer` when `XAI_API_KEY` is set
4. Persist first `evals/results/` numbers from a real catalog when ingest is available
5. Smoke live ingest when `SEC_USER_AGENT` + network are available

**Blockers / Notes**
- Lexical reranker is deterministic and interview-defendable as a baseline; swap to Cohere/BGE without changing `Reranker` protocol
- Hash embedder still used; do not treat demo ablation ranks as quality claims
- Live ingest still needs a valid `SEC_USER_AGENT` and EDGAR access
- Chunking not yet refined from real failure analysis (no live failures yet)

**Eval metrics**
- Harness unchanged this iteration; no live-catalog numbers. Demo composite still expected > 0.5.

---

## Iteration 4 — 2026-08-30 16:01 IST

**Completed**
- Week 1 Day 5 thin eval + README stabilization (see git history for full prior entries).

**Current Status**
- See iterations 0–5 below in repo history and remaining sections kept in this file through Iteration 0.

---

## Iteration 3 — 2026-08-30 15:00 IST

See prior commit history for full text; summary: grounded extractive generation landed.

---

## Iteration 2 — 2026-08-30 14:01 IST

See prior commit history; summary: hybrid retrieve + in-memory index landed.

---

## Iteration 1 — 2026-08-30 13:20 IST

See prior commit history; summary: ingestion pipeline scaffold landed.

---

## Iteration 0 — Bootstrap (2026-08-30)

**Completed**
- Created GitHub repository: https://github.com/nuwanda94/fintruth-rag
- Added README.md with project overview, scope, stack, and structure
- Added ROADMAP.md (full interview-max week-by-week plan — single source of truth)
- Initialized this PROGRESS.md
