# Failure Analysis

First pass from the **demo** eval path (Week 2 Day 5). Corpus is the
13-chunk `DEMO_CORPUS` in `src/fintruth/eval/runner.py`, not live EDGAR
filings. Treat every score as a wiring / policy check.

Source of truth for gold labels: `evals/questions.jsonl` (n=34).
Harness: `run_eval(..., demo=True)` forces extractive generation.

## 1. What the demo harness can and cannot prove

Can prove:

- Out-of-corpus tickers refuse (`q015` TSLA, `q029` BRK, `q031` TSLA).
- Easy single-ticker risk/MD&A items retrieve the matching snippet and
  emit `Sources:` (`q001` AAPL competition is the smoke test).
- Multi-ticker questions refuse when one named issuer is missing from
  the hit list (`should_refuse` missing-ticker rule).
- Exact-figure questions that name a year missing from chunk text refuse
  (`q016` Q3 2019, `q030` FY2012) instead of quoting nearby iPhone revenue.
- Exact-figure questions whose year is only far from any quantity refuse
  (iteration 19 / year-quantity window).
- Comparison answers cite every named issuer (`select_quote_indices` +
  `missing_cited_tickers`).
- Keyword checks use the answer + **cited** spans only (iteration 14).
- Comparison keywords are issuer-aligned (`keywords_by_ticker`, iteration 15).
- Cited spans are resolved by **chunk_id**, not retrieve-list index
  (iteration 16 / F8).

Cannot prove:

- Embedding quality (hash embedder).
- Reranker lift vs Cohere.
- Section parser recall on real 10-K HTML.
- Numerical faithfulness against actual tables.

`tests/test_eval.py` only asserts demo composite `> 0.5` and a handful
of refusal/citation checks. That floor is intentional.

## 2. Failure modes observed or designed into the question bank

### F1. Out of corpus (expected refuse — working)

| IDs | Symptom | Root cause | Status |
|-----|---------|------------|--------|
| q015, q031 | Tesla questions | TSLA not in demo payloads or default ticker list | Refuse via empty / low-overlap hits |
| q029 | Berkshire cybersecurity | BRK not ingested | Same |

Keep these even after live ingest: TSLA/BRK stay outside the 10-name
universe unless the ticker list changes.

### F2. Numerical facts that are not in any chunk (expected refuse — working after period + proximity gates)

| IDs | Symptom | Root cause | Status |
|-----|---------|------------|--------|
| q016 | AAPL Q3 2019 Greater China iPhone units | Demo has no 10-Q and no units | Refuse: year 2019 absent from text |
| q030 | AAPL FY2012 Greater China units | Outside year window + not in text | Refuse: year 2012 absent from text |

Iteration 11 residual: term-overlap let the FY2024 `$201 billion` MD&A
chunk answer q030. Iteration 12 `should_refuse` requires exact-figure
questions to see the asked year in chunk **text** (filing_date is not
enough). Qualitative MD&A (`q002`) is unchanged.

Iteration 19: `evidence_has_year_near_quantity` also requires that year
to sit within `YEAR_QUANTITY_WINDOW` of a dollar / grouped / scaled
figure. A 2012 store-opening sentence followed later by FY2024 revenue
is not period evidence. Bare `2012` is not treated as a quantity.

Residual after live ingest: a year that sits next to the *wrong* figure
can still pass the generation gate; `score_numerical` + the unit-volume
gate must catch that. This is not sentence parsing or XBRL.

### F3. Notes / goodwill sparse section (expected refuse on demo)

| IDs | Symptom | Root cause | Status |
|-----|---------|------------|--------|
| q018, q033 | Goodwill impairment in notes | Demo corpus has no `section=notes` chunks | Filter + overlap refuse |

After live ingest this becomes a real parser/chunker test. If notes are
still empty, the correct behavior remains refuse, not inventing "none".

### F4. Multi-ticker coverage gaps (citation-set + cited-keyword + per-issuer gates — working offline)

| IDs | Symptom | Root cause | Status |
|-----|---------|------------|--------|
| q013 | AAPL iPhone vs MSFT Azure | Both MD&A chunks exist in demo | Answer; citations must include both |
| q025 | META vs GOOGL regulation | Both risk chunks exist | Same |
| q032 | XOM climate vs UNH medical | Different sections; filters leave `sections=[]` | Relies on hybrid + quote cover |

Policy: if the question names ≥2 tickers and any named ticker is missing
from retrieved payloads, refuse. Iteration 13 also requires those tickers
in the **citation set**, not just the retrieve pool. Extractive selection
picks one overlapping chunk per named issuer before filling remaining
slots by rank. An LLM completion that only cites one side is refused.

Iteration 14: `score_keywords` reads answer + cited chunk text only.
Multi-ticker items with ≥2 gold keywords use AND so an uncited neighbor
cannot complete the contrast.

Iteration 15: `keywords_by_ticker` on q013 / q025 / q032 requires each
needle in *that issuer's cited spans*. AAPL "revenue" no longer satisfies
the MSFT side of q013.

### F5. Keyword / section mismatch

Examples: q022 asks for Alphabet "regulation" while the demo sentence
says "regulation" inside "competition and regulation" — easy hit.
q008 "content-moderation" is not required as a keyword; gold keyword is
"regulatory". Live 10-K language will diverge ("content governance",
"Trust & Safety"). Hash embeddings will not rescue paraphrase.

### F6. Score floor false refuses

`DEFAULT_MIN_SCORE = 0.012` is tuned for RRF magnitudes (~0.03 for a
single-list hit). Dense-only cosine from the hash embedder can sit near
that floor on short queries. If an ablation arm uses `mode=dense` and
refuses more than hybrid, that is a metric artifact until real embeddings
land.

### F7. Extractive answers are not synthesis

`extractive_answer` pastes up to three overlapping snippets. Comparison
questions (q013, q025, q032) look like two bullets, not a contrast.
That is acceptable for interview-max. Week 3 LangGraph + Grok should still
be gated: uncited or one-sided synthesis is refused.

### F8. Citation index vs payload identity (chunk_id resolve — working offline)

Citations keep 1-based positions in the **retrieved list** in the prose
so the model can emit `[n]`. Footer still includes `chunk_id`. Eval no
longer grades evidence by index alone: `resolve_cited_chunk` prefers
`Citation.chunk_id`, then falls back to index. A rerank shuffle that
swaps position 1 cannot move keywords onto a neighbor span. A citation
whose `chunk_id` is missing from the current pool fails
`citation_support`.

## 3. Priority fixes (do not expand scope)

1. Persist `evals/results/latest.json` from `make eval` once a writable
   checkout runs the harness (numbers will still be demo until ingest).
2. After first live catalog: re-run the 34 and tag each residual miss
   as retrieve / filter / refuse-policy / generation.
3. ~~Gold numeric spans for live q016/q030-class items still need a unit parser~~
   **done offline (iterations 17 + 19)**; live catalog still needed to measure IR.
4. ~~Require all named tickers in the citation set~~ **done (iteration 13)**.
5. ~~Keyword metric must not use the uncited retrieve pool~~ **done (iteration 14)**.
6. ~~Per-issuer keyword alignment on comparisons~~ **done (iteration 15)**.
7. ~~Grade cited evidence by chunk_id, not list index~~ **done (iteration 16)**.
8. Do not raise chunk size or swap embedders based on demo scores.

## 4. Demo metric contract (regression guard)

From `tests/test_eval.py`:

- `n >= 30` questions loaded
- at least one `expect_refuse` and one `out_of_corpus` / `multi_ticker`
- demo composite `> 0.5`
- q015, q029, and q030 refuse
- q001 answers with citations and a `Sources:` footer
- q013 / q025 / q032 remain keyword-ok on *per-issuer* cited spans
- shuffled retrieve lists still resolve keywords via `chunk_id`

If composite collapses below 0.5, the refuse policy or demo corpus
regressed. Do not "fix" it by deleting hard questions.
