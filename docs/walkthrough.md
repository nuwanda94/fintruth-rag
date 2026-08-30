# 10–15 Minute Interview Walkthrough

Rehearsal script for Week 3 Day 5. Demo corpus only unless ingest has run.

## 0. Frame (60s)

FinTruth is a *strictly grounded* SEC research assistant. Scope is 8–12 large-caps, MD&A + Risk Factors, hybrid retrieve + filters + rerank, extractive citations, and an explicit refuse path. Out of scope: multi-hop tools, XBRL, live news.

## 1. Architecture (2 min)

Ingest → section chunks → hybrid dense+sparse RRF → lexical rerank → grade → generate or refuse.

Point at `docs/architecture.md`. Offline default is hash embeddings + `InMemoryVectorStore` so the loop is deterministic without keys. Call out grade gate 5: exact-figure + year must appear in chunk *text*.

## 2. Live easy query (2 min)

```bash
make ask
# or Streamlit: make ui
```

Ask: *What competition risks does Apple disclose?*

Show: answer text, `[n]` citations, chunk scores, ticker/section/date, retrieve ms vs graph ms.

## 3. Live hard / refuse query (2 min)

Ask: *Did Tesla disclose Cybertruck unit deliveries in its latest 10-K?*

Show the refusal banner (missing issuer). Follow with *What was Apple's exact FY2012 greater-China iPhone unit volume?* — that refuses because 2012 is not in the FY2024 MD&A snippet, even though "iPhone" overlaps.

Explain grade gates (`should_refuse`) plus extractive generator still refusing if grade is optimistic.

## 4. Eval + ablation (3 min)

```bash
make eval
```

Open `evals/results/latest.json`:

- n=34 seeded items including out-of-corpus and one gold number (`q002` / `$201` fixture)
- contract metrics: refusal, citation presence, citation ticker support, keyword, ticker, numerical
- retrieval ablation arms: dense / hybrid / hybrid+rerank (keyword-in-top-k on the **demo** fixture — not IR quality)

`q030` is the designed period-absent case; after the period gate it should refuse. See `evals/failure_analysis.md`.

## 5. Decisions and limits (2 min)

Walk D1–D10 in `docs/design_decisions.md` and the first page of `docs/limitations.md`. Emphasize: hash embedder is wiring; demo `$201 billion` is a harness figure; Grok is optional.

## 6. What more time buys (1 min)

Live EDGAR catalog + voyage/Cohere + RAGAS on real filings; parent-document chunks; numerical unit parser. Do not promise multi-hop agents in this package.

Live ingest is gated: `make ingest-preflight` then
`uv run python scripts/ingest.py --tickers AAPL --years 1 --max-filings 1`
once `SEC_USER_AGENT` is a real name + email. Tag meaning: `CHANGELOG.md` / `0.1.0`.
