# FinTruth RAG — Progress Log

This file is the running log of automated and manual iterations.  
Every run must append a new entry at the top (most recent first).

---

## Iteration 12 — 2026-08-31 00:00 IST

**Completed**
- Week 3 Day 5 sharp-edge: stop answering exact-figure questions from the wrong fiscal year.
  - `src/fintruth/generation/chain.py` — `asks_exact_figure` + `question_years`; `should_refuse` if the asked year is missing from chunk **text** (not `filing_date`)
  - Fixes demo residual `q030` (FY2012 greater-China units were being answered from FY2024 `$201 billion` iPhone revenue)
  - `tests/test_generation.py` — period-absent refuse, period-present answer, qualitative MD&A still answers; LLM refusal prefix uses an overlapping question so the model path is actually tested
  - `tests/test_chunker.py` — SAMPLE_HTML bodies exceed the 200-char section floor so Item 1A / Item 7 parse instead of collapsing to `full_filing`
  - Docs: `architecture.md` grade-gate list, `walkthrough.md` q030 live refuse, `CHANGELOG.md`, this log
  - `evals/results/latest.json` demo snapshot: n=34, all contract metrics 1.0, `failed_ids=[]` (verified with `run_eval(demo=True)`)

**Current Status**
- Week 1: foundation + offline end-to-end loop + thin eval **done**
- Week 2: retrieval hardening + grounding/refusal + first-pass analysis **done offline**
- Week 3 Days 1–5: graph + Streamlit + eval docs + rehearsal + ingest preflight + period gate **done offline**
- Interview-max offline package is complete; live EDGAR still blocked on a real User-Agent + network
- Git annotated tag `v0.1.0` **not created** (no create-tag tool); changelog is the contract

**Next Iteration Should Pick Up**
1. With a real `SEC_USER_AGENT`, run `make ingest-preflight` then `--tickers AAPL --years 1 --max-filings 1`
2. If chunks land, `scripts/index.py` + `scripts/run_eval.py` (no `--demo`) and refresh `evals/results/latest.json` only if the catalog is non-empty
3. Create annotated tag locally: `git tag -a v0.1.0 -m "interview-max offline"` (optional)
4. Rehearse `docs/walkthrough.md` against Streamlit; the new FY2012 refuse should appear in the hard-query slot
5. Do not add RAGAS, multi-hop tools, or Docker polish

**Blockers / Notes**
- Default `.env.example` address is intentionally rejected so we never hit EDGAR as `contact@example.com`
- Demo composite 1.0 is a **contract** score on 13 fixture chunks, not IR quality
- Ablation 1.0 scores remain fixture-only

**Eval metrics**
- Demo `run_eval(demo=True)`: n=34, refusal_accuracy=1.0, citation_accuracy=1.0, citation_support=1.0, keyword_hit_rate=1.0, ticker_hit_rate=1.0, numerical_accuracy=1.0, composite=1.0, failed_ids=[]

---

## Iteration 11 — 2026-08-30 23:00 IST

**Completed**
- Week 3 Day 5 follow-on: live-ingest gate + v0.1.0 packaging notes (still offline).
  - `src/fintruth/ingestion/preflight.py` — SEC_USER_AGENT placeholder detect, edgartools import, data dirs; optional `data.sec.gov` GET
  - `scripts/ingest.py --preflight` / `--check-network` / `--max-filings`; live download refused on example User-Agent
  - `download_filings` / `run_ingest` honor per-ticker `max_filings` for a 1-filing smoke
  - `make ingest-preflight`; tests in `tests/test_ingest_preflight.py` + changelog guard in `tests/test_docs.py`
  - `CHANGELOG.md` documents what `v0.1.0` means (create-tag API not available)
  - README / walkthrough / `.env.example` updated so rehearsal matches the gate

**Current Status**
- Week 1: foundation + offline end-to-end loop + thin eval **done**
- Week 2: retrieval hardening + grounding/refusal + first-pass analysis **done offline**
- Week 3 Days 1–5: graph + Streamlit + eval docs + rehearsal + ingest preflight **done offline**
- Interview-max offline package is complete; live EDGAR still blocked on a real User-Agent + network
- Git annotated tag `v0.1.0` **not created** (no create-tag tool); changelog is the contract

**Next Iteration Should Pick Up**
1. With a real `SEC_USER_AGENT`, run `make ingest-preflight` then `--tickers AAPL --years 1 --max-filings 1`
2. If chunks land, `scripts/index.py` + `scripts/run_eval.py` (no `--demo`) and refresh `evals/results/latest.json` only if the catalog is non-empty
3. Create annotated tag locally: `git tag -a v0.1.0 -m "interview-max offline"` (optional)
4. Rehearse `docs/walkthrough.md` against Streamlit; fix only script-breaking edges
5. Do not add RAGAS, multi-hop tools, or Docker polish

**Blockers / Notes**
- Default `.env.example` address is intentionally rejected so we never hit EDGAR as `contact@example.com`
- Demo snapshot residual miss remains `q030`
- Ablation 1.0 scores are fixture-only

**Eval metrics**
- Unchanged demo run in `evals/results/latest.json`: n=34, composite ≈ 0.990

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
