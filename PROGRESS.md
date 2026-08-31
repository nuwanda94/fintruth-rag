# FinTruth RAG — Progress Log

This file is the running log of automated and manual iterations.  
Every run must append a new entry at the top (most recent first).

---

## Iteration 21 — 2026-08-31 10:00 IST

**Completed**
- Week 2 Day 5 / F2 residual: year next to the right *kind* of figure but the
  wrong reporting segment.
  - `src/fintruth/generation/segments.py` — `question_segments`,
    `evidence_has_year_near_segment`
  - `src/fintruth/generation/refuse.py` — exact-figure + named segment
    requires the asked year window to contain that segment phrase
  - `tests/test_period_proximity.py` — FY2012 Americas units refuses a
    Greater China unit-volume ask; co-located Greater China units still answers
  - Docs: architecture gate 9, limitations, failure_analysis F2, walkthrough,
    CHANGELOG 0.1.9

**Current Status**
- Week 1–3 interview-max offline package remains complete
- F2 live-ingest risk (year + wrong geography) is tighter offline; still
  lexical, not XBRL / product-line roles
- Live EDGAR still blocked on a real User-Agent + network
- Git annotated tag `v0.1.0` **not created** (no create-tag tool)

**Next Iteration Should Pick Up**
1. With a real `SEC_USER_AGENT`, run `make ingest-preflight` then `--tickers AAPL --years 1 --max-filings 1`
2. If chunks land, `scripts/index.py` + `scripts/run_eval.py` (no `--demo`)
3. Optional: `git tag -a v0.1.0 -m "interview-max offline"`
4. Rehearse `docs/walkthrough.md` (easy / TSLA refuse / FY2012 refuse / AAPL vs MSFT)
5. Do not add RAGAS, multi-hop tools, or Docker polish.

**Blockers / Notes**
- Default `.env.example` address is rejected so we never hit EDGAR as `contact@example.com`
- Demo composite 1.0 is a contract score on 13 fixture chunks, not IR quality
- Unit parser is lexical (million/billion/units), not XBRL
- Extractive token counts are char/4 estimates (`source=estimate`)
- Year-quantity / year-unit / year-segment windows are character distance in one chunk
- A year next to the right geography can still be the wrong product line

**Eval metrics**
- Unchanged checked-in demo snapshot: n=34, composite=1.0, failed_ids=[]

---

## Iteration 20 — 2026-08-31 08:00 IST

**Completed**
- Week 2 Day 5 / F2 residual: year next to the *wrong kind* of figure.
  - `src/fintruth/generation/units.py` — export `UNIT_QUANTITY_RE`
  - `src/fintruth/generation/refuse.py` — `evidence_has_year_near_quantity(..., quantity_re=)`;
    unit-volume + year now requires the year window to contain units, not dollars
  - `tests/test_period_proximity.py` — FY2012 `$22.8 billion` + FY2024 units refuses
    an FY2012 unit-volume ask
  - Docs: architecture gate 7, limitations, failure_analysis F2, CHANGELOG 0.1.8

**Current Status**
- Week 1–3 interview-max offline package remains complete
- F2 live-ingest risk (year + wrong figure kind in the same chunk) is tighter
  offline; still lexical, not XBRL / line-item roles
- Live EDGAR still blocked on a real User-Agent + network
- Git annotated tag `v0.1.0` **not created** (no create-tag tool)

**Next Iteration Should Pick Up**
1. With a real `SEC_USER_AGENT`, run `make ingest-preflight` then `--tickers AAPL --years 1 --max-filings 1`
2. If chunks land, `scripts/index.py` + `scripts/run_eval.py` (no `--demo`)
3. Optional: `git tag -a v0.1.0 -m "interview-max offline"`
4. Rehearse `docs/walkthrough.md` (easy / TSLA refuse / FY2012 refuse / AAPL vs MSFT)
5. Do not add RAGAS, multi-hop tools, or Docker polish.

**Blockers / Notes**
- Default `.env.example` address is rejected so we never hit EDGAR as `contact@example.com`
- Demo composite 1.0 is a contract score on 13 fixture chunks, not IR quality
- Unit parser is lexical (million/billion/units), not XBRL
- Extractive token counts are char/4 estimates (`source=estimate`)
- Year-quantity / year-unit windows are character distance in one chunk
- A year next to the right *kind* of figure can still be the wrong geography/line item

**Eval metrics**
- Unchanged checked-in demo snapshot: n=34, composite=1.0, failed_ids=[]

---

## Iteration 19 — 2026-08-31 07:00 IST

**Completed**
- Week 2 Day 5 / F2 residual: exact-figure year must sit near a quantity.
  - `src/fintruth/generation/refuse.py` — `evidence_has_year_near_quantity`,
    `_FACT_QUANTITY` (dollars / grouped thousands / scaled counts; bare years
    are not quantities), `YEAR_QUANTITY_WINDOW=96`
  - `should_refuse` now refuses when the asked year is in the chunk but only
    far from any figure ("not near a quantity")
  - `tests/test_period_proximity.py` — distant 2012 store-opening vs FY2024
    revenue; co-located unit volume still answers
  - Docs: architecture gate 6 inserted; CHANGELOG 0.1.7

**Current Status**
- Week 1–3 interview-max offline package remains complete
- F2 live-ingest risk (year + unrelated figure in the same chunk) is tighter
  offline; still lexical, not XBRL
- Live EDGAR still blocked on a real User-Agent + network
- Git annotated tag `v0.1.0` **not created** (no create-tag tool)

**Next Iteration Should Pick Up**
1. With a real `SEC_USER_AGENT`, run `make ingest-preflight` then `--tickers AAPL --years 1 --max-filings 1`
2. If chunks land, `scripts/index.py` + `scripts/run_eval.py` (no `--demo`)
3. Optional: `git tag -a v0.1.0 -m "interview-max offline"`
4. Rehearse `docs/walkthrough.md` (easy / TSLA refuse / FY2012 refuse / AAPL vs MSFT)
5. Do not add RAGAS, multi-hop tools, or Docker polish.

**Blockers / Notes**
- Default `.env.example` address is rejected so we never hit EDGAR as `contact@example.com`
- Demo composite 1.0 is a contract score on 13 fixture chunks, not IR quality
- Unit parser is lexical (million/billion/units), not XBRL
- Extractive token counts are char/4 estimates (`source=estimate`)
- Year-quantity window is character distance in one chunk, not sentence parse

**Eval metrics**
- Unchanged checked-in demo snapshot: n=34, composite=1.0, failed_ids=[]

---

## Iteration 18 — 2026-08-31 06:03 IST

**Completed**
- Week 2 Days 1–2 perf residual: latency + token tracking (still interview-max).
  - `src/fintruth/generation/usage.py` — `TokenUsage`, `estimate_tokens` (char/4),
    `usage_from_api`, `measure_usage`
  - `GroundedAnswer.usage` attached on extractive, LLM, and refuse paths
  - `complete_with_grok_detailed` keeps provider usage when Grok returns it
  - `GraphRun.retrieve_ms` / `generate_ms` / `usage`
  - Streamlit metrics for generate ms + prompt/completion tokens
  - `tests/test_usage.py`
  - Docs: architecture, limitations, walkthrough gate numbering, CHANGELOG 0.1.6

**Current Status**
- Week 1–3 interview-max offline package remains complete
- Week 2 token-accounting residual is done offline (estimates, not billed tokens)
- Live EDGAR still blocked on a real User-Agent + network
- Git annotated tag `v0.1.0` **not created** (no create-tag tool)

**Next Iteration Should Pick Up**
1. With a real `SEC_USER_AGENT`, run `make ingest-preflight` then `--tickers AAPL --years 1 --max-filings 1`
2. If chunks land, `scripts/index.py` + `scripts/run_eval.py` (no `--demo`)
3. Optional: `git tag -a v0.1.0 -m "interview-max offline"`
4. Rehearse `docs/walkthrough.md` (easy / TSLA refuse / FY2012 refuse / AAPL vs MSFT)
5. Do not add RAGAS, multi-hop tools, or Docker polish.

**Blockers / Notes**
- Default `.env.example` address is rejected so we never hit EDGAR as `contact@example.com`
- Demo composite 1.0 is a contract score on 13 fixture chunks, not IR quality
- Unit parser is lexical (million/billion/units), not XBRL
- Extractive token counts are char/4 estimates (`source=estimate`)

**Eval metrics**
- Unchanged checked-in demo snapshot: n=34, composite=1.0, failed_ids=[]

---

## Iteration 17 — 2026-08-31 05:02 IST

**Completed**
- Week 2 Day 5 residual from `evals/failure_analysis.md` F2 / priority 3:
  unit-aware numerical checks + unit-volume generation gate.
  - `src/fintruth/eval/metrics.py` — `Quantity`, `parse_quantity`,
    `extract_quantities`, `quantities_cover`; scaled gold tokens
  - `src/fintruth/generation/units.py` — `asks_unit_volume`,
    `evidence_has_unit_quantity`
  - `src/fintruth/generation/refuse.py` — exact unit asks refuse dollar-only evidence
  - Generation package split for reviewability: `citations.py`, `refuse.py`,
    `generate.py` (public API still `fintruth.generation.chain`)
  - `tests/test_units.py` — scale mismatch + FY2012 revenue ≠ unit volume
  - Docs: `docs/architecture.md` gate 6, `docs/limitations.md`, `CHANGELOG.md` 0.1.5

**Current Status**
- Week 1–3 interview-max offline package remains complete
- F2 unit-parser residual is done offline
- Live EDGAR still blocked on a real User-Agent + network
- Git annotated tag `v0.1.0` **not created** (no create-tag tool)

**Next Iteration Should Pick Up**
1. With a real `SEC_USER_AGENT`, run `make ingest-preflight` then `--tickers AAPL --years 1 --max-filings 1`
2. If chunks land, `scripts/index.py` + `scripts/run_eval.py` (no `--demo`)
3. Optional: `git tag -a v0.1.0 -m "interview-max offline"`
4. Rehearse `docs/walkthrough.md` (easy / TSLA refuse / FY2012 refuse / AAPL vs MSFT)
5. Do not add RAGAS, multi-hop tools, or Docker polish.

**Blockers / Notes**
- Default `.env.example` address is rejected so we never hit EDGAR as `contact@example.com`
- Demo composite 1.0 is a contract score on 13 fixture chunks, not IR quality
- Unit parser is lexical (million/billion/units), not XBRL

**Eval metrics**
- Unchanged checked-in demo snapshot: n=34, composite=1.0, failed_ids=[]

---

## Iteration 16 — 2026-08-31 04:01 IST

See git history: citation identity follows `chunk_id` after retrieve shuffle.

---

## Iterations 0–15

See git history on `main`. ROADMAP.md remains the single source of truth.
