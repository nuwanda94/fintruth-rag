# FinTruth RAG — Progress Log

This file is the running log of automated and manual iterations.  
Every run must append a new entry at the top (most recent first).

---

## Iteration 9 — 2026-08-30 21:10 IST

**Completed**
- Week 3 Days 3–4 evaluation depth + interview docs (offline-first):
  - `src/fintruth/eval/metrics.py` — `extract_numbers`, `score_numerical`, `score_citation_support`; ItemScore now includes `numerical_ok` + `citation_support_ok`; summary adds `numerical_accuracy` and `citation_support`
  - `src/fintruth/eval/dataset.py` — optional `expected_numbers` on `EvalQuestion`
  - `src/fintruth/eval/ablation.py` — dense vs hybrid vs hybrid+rerank keyword-in-top-k
  - `src/fintruth/eval/runner.py` — demo AAPL MD&A chunk now carries `$201 billion`; `run_eval(..., with_ablation=True)` persists ablation next to scores
  - `evals/questions.jsonl` — q002 gold number `201`
  - `tests/test_eval.py` — numerical faithfulness, foreign-ticker citation reject, `latest.json` write to tmp, ablation arms
  - `docs/limitations.md` and `docs/exceptional_work.md` filled (no longer stubs)
  - README Streamlit walkthrough + metric description; `scripts/run_eval.py --no-ablation`

**Current Status**
- Week 1: foundation + offline end-to-end loop + thin eval **done**
- Week 2: retrieval hardening + grounding/refusal + first-pass analysis **done offline**
- Week 3 Days 1–2: graph + Streamlit **done offline**
- Week 3 Days 3–4: custom numerical + citation-support checks + ablation helper + limitations/exceptional_work **done offline**
- Week 3 Day 5: rehearsal / release tag **not started**
- Live catalog ingest / RAGAS / published IR numbers **not started**

**Next Iteration Should Pick Up**
1. Week 3 Day 5: sharp-edge pass — persist a checked-in `evals/results/latest.json` from `make eval --demo` if the workspace is writable; tag a clean release if desired
2. Smoke live ingest when `SEC_USER_AGENT` + EDGAR are available
3. Optional: latency display in Streamlit; do not add RAGAS or multi-hop tools (out of remaining interview-max buffer unless time remains)

**Blockers / Notes**
- Demo `$201 billion` is a fixture figure for the numerical contract, not an SEC-extracted fact
- Ablation keyword-in-top-k on hash embeddings is a harness check, not a quality claim
- Writing `evals/results/` in CI still depends on a writable checkout; tests use tmp_path

**Eval metrics**
- Question bank n=34 with one gold-number item (q002). Composite contract unchanged (`> 0.5`). New summary keys: `numerical_accuracy`, `citation_support`.

---

## Iteration 8 — 2026-08-30 20:01 IST

**Completed**
- Week 3 Days 1–2 minimal truth-seeking loop + evidence UI (offline-first):
  - `src/fintruth/agent/graph.py` — `TruthSeekingGraph` retrieve → grade → generate|refuse; typed `AgentState` / `GraphRun`; optional `compile_langgraph` when the extra is installed
  - `src/fintruth/ui/app.py` — Streamlit demo: answer, refusal banner, citations, expandable chunk scores/metadata, ticker/section/as-of filters over `DEMO_CORPUS`
  - `tests/test_agent_graph.py` — generate path on Apple competition, refuse empty grade, ticker filter
  - `docs/architecture.md` — graph node in the pipeline diagram
  - Makefile `ui` target; `langgraph` added to the optional `index` extra

**Current Status**
- Week 1: foundation + offline end-to-end loop + thin eval **done**
- Week 2: retrieval hardening + grounding/refusal + first-pass analysis **done offline**
- Week 3 Days 1–2: graph + Streamlit **done offline** (LangGraph compile is optional, not the default test path)
- Week 3 Days 3–4: custom numerical + citation accuracy, final ablation suite, polished limitations/exceptional_work **not started**
- Live ablation numbers / RAGAS / catalog ingest **not started**

**Next Iteration Should Pick Up**
1. Week 3 Days 3–4: custom numerical + citation-accuracy checks; persist `evals/results/` when a writable checkout exists
2. Fill `docs/limitations.md` and `docs/exceptional_work.md` (currently stubs)
3. Polish README walkthrough for the Streamlit demo
4. Smoke live ingest when `SEC_USER_AGENT` + EDGAR are available

**Blockers / Notes**
- Default graph is a typed state machine so pytest stays extra-free; `compile_langgraph` is the interview-aligned optional wrapper
- UI imports Streamlit only inside `main()`; helpers are importable without the extra
- Hash embedder / demo corpus still not quality claims

**Eval metrics**
- Question bank n=34. Demo composite contract unchanged. No new live-catalog numbers.

---

## Iteration 7 — 2026-08-30 19:05 IST

**Completed**
- Week 2 Day 5 analysis pass (no live catalog; docs grounded in code + demo eval):
  - `docs/design_decisions.md` — D1–D9 (offline-first, section chunks, hybrid RRF, lexical reranker, as_of cutoff, extractive+gates, refusal-labeled eval, binary metrics, in-memory store) plus explicit OUT list
  - `evals/failure_analysis.md` — F1–F8 from the 34-question bank vs `DEMO_CORPUS` (out-of-corpus, numerical-absent, notes-sparse, multi-ticker gaps, keyword drift, score-floor artifacts, extractive-not-synthesis, citation index identity)
  - `docs/architecture.md` — first pipeline diagram matching current modules
  - `tests/test_docs.py` — docs stay non-empty and mention demo failure IDs

**Current Status**
- Week 1: foundation + offline end-to-end loop + thin eval **done**
- Week 2 Days 1–2: reranker + as-of + ablation helper **done offline**
- Week 2 Days 3–4: grounding/refusal + 34-question set **done offline**
- Week 2 Day 5: design_decisions + failure_analysis **first pass done** (demo-only evidence)
- Week 3 Days 1–2: LangGraph + Streamlit **not started**
- Live ablation numbers / RAGAS / `evals/results/*.json` from a real run **not started**

**Next Iteration Should Pick Up**
1. Week 3 Days 1–2: minimal LangGraph retrieve → grade → generate or refuse (`src/fintruth/agent/graph.py`)
2. Streamlit evidence UI (`src/fintruth/ui/app.py`): answer, expandable chunks/scores/metadata, citations, refusal indicator
3. Persist `evals/results/` from `make eval` when a writable checkout is available
4. Smoke live ingest when `SEC_USER_AGENT` + EDGAR are available

**Blockers / Notes**
- Docs explicitly forbid treating hash-embedder demo ranks as quality claims
- Grok path still optional; eval harness stays extractive
- Live catalog numbers still blocked on ingest credentials

**Eval metrics**
- Question bank n=34. Demo composite contract unchanged (`> 0.5` in `tests/test_eval.py`). No new live-catalog numbers this iteration.

---

## Iteration 6 — 2026-08-30 18:02 IST

**Completed**
- Week 2 Days 3–4 generation / refusal / eval-set expansion (offline-first). See git history for full text.

---

## Iteration 5 — 2026-08-30 17:00 IST

See prior commit history; summary: reranker + as-of + ablation helper.

---

## Iteration 4 — 2026-08-30 16:01 IST

See prior commit history; summary: thin eval + README stabilization.

---

## Iteration 3 — 2026-08-30 15:00 IST

See prior commit history; summary: grounded extractive generation landed.

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
