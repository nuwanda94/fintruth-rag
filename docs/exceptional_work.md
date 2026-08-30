# Exceptional Work One-Pager

What to walk through in a 10–15 minute interview. Every claim below is grounded in this repo, not in unpublished live-catalog numbers.

## Problem choice

Financial Q&A fails when systems invent figures, mix issuers, or answer from the wrong year. FinTruth is scoped to **SEC 10-K/10-Q MD&A + Risk Factors**, with an explicit refusal path when evidence is missing.

## Architecture you can draw

```
ingest sections → chunk + metadata → embed + sparse index
    → dense + BM25 + RRF + filters + lexical rerank
    → grade (score floor, term overlap, multi-ticker coverage)
    → extractive (or gated Grok) answer with [n] citations
    → refuse if any gate fails
```

Default graph is a typed state machine (`TruthSeekingGraph`). LangGraph is an optional compile of the same nodes so pytest stays extra-free.

## Design decisions worth defending (see `docs/design_decisions.md`)

1. **Offline-first** so every PR has a working retrieve → cite → refuse loop without API keys.
2. **Section chunks + metadata filters** instead of raw full-filing embeddings.
3. **Hybrid RRF** rather than dense-only; sparse carries exact risk language ("fulfillment", "wearables").
4. **Extractive + gates** rather than free-form generation as the eval default.
5. **Refusal-labeled eval items** (`out_of_corpus`, `numerical_absent`, `notes_sparse`) so silence is scored, not just fluency.

## What the harness actually measures

- 34-question bank in `evals/questions.jsonl`.
- Binary metrics: refusal accuracy, citation presence, citation ticker support, keyword hit, ticker hit, optional numerical faithfulness (`expected_numbers` on items such as q002 / $201).
- Retrieval ablation helper: dense vs hybrid vs hybrid+rerank keyword-in-top-k (`src/fintruth/eval/ablation.py`).
- Failure modes F1–F8 documented against `DEMO_CORPUS` in `evals/failure_analysis.md`.

Demo composite is a **contract test** (`> 0.5` in `tests/test_eval.py`), not a published IR leaderboard.

## Demo script

1. Easy: Apple competition risks → cited risk-factors snippet + Sources footer.
2. Hard refuse: Tesla / Berkshire → refusal banner, empty citations.
3. Numerical-absent: 2019 China iPhone units → refuse rather than invent a figure.
4. Open Streamlit (`make ui`): expandable chunk scores, ticker/section/as-of filters.

## If you had more time

Live EDGAR catalog + voyage-finance-2 + Cohere rerank + RAGAS on 40 hard questions; parent-document retrieval for notes; table/XBRL path for true numerical QA.
