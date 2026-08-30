# FinTruth RAG — Progress Log

This file is the running log of automated and manual iterations.  
Every run must append a new entry at the top (most recent first).

---

## Iteration 14 — 2026-08-31 02:00 IST

**Completed**
- Week 3 Day 5 sharp-edge from `evals/failure_analysis.md` F4 residual / priority 5:
  keyword metric must not credit the uncited retrieve pool.
  - `src/fintruth/eval/metrics.py` — `score_keywords` + `_cited_haystack`;
    multi_ticker with ≥2 gold keywords uses AND over cited+answer text.
  - `tests/test_eval.py` — uncited-pool false positive; multi-ticker AND;
    demo q013/q025/q032 still keyword-ok.
  - Docs: `evals/failure_analysis.md`, `docs/architecture.md`, `CHANGELOG.md` 0.1.2.

**Current Status**
- Week 1: foundation + offline end-to-end loop + thin eval **done**
- Week 2: retrieval hardening + grounding/refusal + first-pass analysis **done offline**
- Week 3 Days 1–5: graph + Streamlit + eval docs + rehearsal + ingest preflight
  + period gate + multi-ticker citation cover + cited-keyword scoring **done offline**
- Interview-max offline package is complete; live EDGAR still blocked on a real User-Agent + network
- Git annotated tag `v0.1.0` **not created** (no create-tag tool); changelog is the contract

**Next Iteration Should Pick Up**
1. With a real `SEC_USER_AGENT`, run `make ingest-preflight` then `--tickers AAPL --years 1 --max-filings 1`
2. If chunks land, `scripts/index.py` + `scripts/run_eval.py` (no `--demo`) and refresh `evals/results/latest.json` only if the catalog is non-empty
3. Create annotated tag locally: `git tag -a v0.1.0 -m "interview-max offline"` (optional)
4. Rehearse `docs/walkthrough.md` against Streamlit (easy / TSLA refuse / FY2012 refuse / AAPL vs MSFT cite-both)
5. Do not add RAGAS, multi-hop tools, or Docker polish. Optional later: per-issuer keyword alignment on comparisons.

**Blockers / Notes**
- Default `.env.example` address is intentionally rejected so we never hit EDGAR as `contact@example.com`
- Demo composite 1.0 is a **contract** score on 13 fixture chunks, not IR quality
- Ablation 1.0 scores remain fixture-only
- Did not re-run `run_eval(demo=True)` write in this environment; snapshot `evals/results/latest.json` is still the iteration-12 contract file

**Eval metrics**
- Unchanged checked-in demo snapshot: n=34, composite=1.0, failed_ids=[]
- Keyword policy change is covered by unit tests; refresh snapshot on the next writable harness run

---

## Iteration 13 — 2026-08-31 01:00 IST

**Completed**
- Week 3 Day 5 sharp-edge from `evals/failure_analysis.md` priority 4:
  require every named issuer in the **citation set** on multi-ticker questions.
  - `src/fintruth/generation/chain.py` — `select_quote_indices` covers named
    tickers before rank; `missing_cited_tickers` refuses one-sided extracts
    and one-sided LLM completions; fixed `GroundedAnswer.sources_block`.
  - `src/fintruth/eval/metrics.py` — `multi_ticker` items need `wanted <= cited`.
  - `tests/test_generation.py` — quote cover, extractive both-issuer answer,
    LLM omit-ticker refuse.
  - Streamlit walkthrough prompt buttons in `src/fintruth/ui/app.py`.
  - Docs: architecture gate 6, walkthrough compare slot, failure F4 + priority 4 done,
    `CHANGELOG.md` 0.1.1.

**Current Status**
- Week 1–3 interview-max offline package complete except live EDGAR.

**Next Iteration Should Pick Up**
See Iteration 14.

---

## Iteration 12 — 2026-08-31 00:00 IST

**Completed**
- Period gate for exact-figure questions (`q030`). See git history.

---

## Iteration 11 — 2026-08-30 23:00 IST

See git history for ingest preflight + v0.1.0 packaging notes.

---

## Iteration 10 — 2026-08-30 22:00 IST

See git history.

---

## Iteration 9 — 2026-08-30 21:10 IST

See git history: Week 3 Days 3–4 evaluation depth + interview docs.

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
