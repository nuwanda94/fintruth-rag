# FinTruth RAG — Progress Log

This file is the running log of automated and manual iterations.  
Every run must append a new entry at the top (most recent first).

---

## Iteration 10 — 2026-08-30 22:00 IST

**Completed**
- Week 3 Day 5 sharp-edge + packaging pass (offline-first):
  - Checked in `evals/results/latest.json` from a live `run_eval(demo=True)` (n=34, composite ≈ 0.990; residual miss `q030`)
  - `.gitignore` keeps `evals/results/latest.json` while ignoring stamped `run_*.json`
  - `GraphRun.latency_ms`; Streamlit shows retrieve ms + graph ms
  - Issuer-aware refusal: company names map to tickers; missing issuer in hits → refuse
  - `docs/walkthrough.md` 10–15 min rehearsal script
  - Tests: graph latency, snapshot contract, walkthrough, Tesla-name refuse

**Current Status**
- Week 1: foundation + offline end-to-end loop + thin eval **done**
- Week 2: retrieval hardening + grounding/refusal + first-pass analysis **done offline**
- Week 3 Days 1–2: graph + Streamlit **done offline**
- Week 3 Days 3–4: custom metrics + ablation + interview docs **done offline**
- Week 3 Day 5: rehearsal script + checked-in demo results + latency UI + issuer refuse **done offline**
- Interview-max offline package is complete
- Live catalog ingest / RAGAS / published IR numbers / git release tag **not started**

**Next Iteration Should Pick Up**
1. Smoke live ingest when `SEC_USER_AGENT` + EDGAR are available; regenerate `latest.json` from catalog if chunks exist
2. Optional git tag `v0.1.0` / GitHub release (create-tag API not in this tool set)
3. Rehearse `docs/walkthrough.md` against Streamlit; fix only script-breaking edges
4. Do not add RAGAS, multi-hop tools, or Docker polish

**Blockers / Notes**
- Demo snapshot residual miss: `q030` (FY2012 greater-China iPhone units) — expected given fixture coverage
- Ablation arms all 1.0 on the tiny demo corpus; do not present as quality
- `$201 billion` remains a harness figure

**Eval metrics**
- Checked-in demo run: n=34, refusal_accuracy=0.971, citation_accuracy=1.0, citation_support=1.0, keyword_hit_rate=1.0, ticker_hit_rate=1.0, numerical_accuracy=0.971, composite=0.990
- Ablation keyword-in-top-k: dense=1.0, hybrid=1.0, hybrid+rerank=1.0 (fixture only)

---

## Iteration 9 — 2026-08-30 21:10 IST

**Completed**
- Week 3 Days 3–4 evaluation depth + interview docs (offline-first). See commit history for file-level detail.

**Current Status**
- Week 3 Day 5 was the next unfinished block at the time.

---

## Iteration 8 — 2026-08-30 20:01 IST

See git history: graph + Streamlit evidence UI.

---

## Iteration 7 — 2026-08-30 19:05 IST

See git history: design_decisions + failure_analysis.

---

## Iteration 6 — 2026-08-30 18:02 IST

See prior commit history; summary: grounding/refusal + eval-set expansion.

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
