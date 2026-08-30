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

### F2. Numerical facts that are not in any chunk (expected refuse)

| IDs | Symptom | Root cause | Status |
|-----|---------|------------|--------|
| q016 | AAPL Q3 2019 Greater China iPhone units | Demo has no 10-Q and no units | Should refuse |
| q030 | AAPL FY2012 Greater China units | Outside year window + not in text | Should refuse |

Risk after live ingest: a nearby MD&A sentence about "iPhone revenue"
may pass term-overlap and answer without the number. Mitigation slated
for Week 3 custom numerical checks (answer must contain the gold figure
or refuse).

### F3. Notes / goodwill sparse section (expected refuse on demo)

| IDs | Symptom | Root cause | Status |
|-----|---------|------------|--------|
| q018, q033 | Goodwill impairment in notes | Demo corpus has no `section=notes` chunks | Filter + overlap refuse |

After live ingest this becomes a real parser/chunker test. If notes are
still empty, the correct behavior remains refuse, not inventing "none".

### F4. Multi-ticker coverage gaps

| IDs | Symptom | Root cause | Status |
|-----|---------|------------|--------|
| q013 | AAPL iPhone vs MSFT Azure | Both MD&A chunks exist in demo | Should answer if both pass filters |
| q025 | META vs GOOGL regulation | Both risk chunks exist | Should answer |
| q032 | XOM climate vs UNH medical | Different sections; filters leave `sections=[]` | Relies on hybrid not dropping one issuer |

Policy: if the question names ≥2 tickers and any named ticker is missing
from retrieved payloads, refuse. That is conservative and interview-
defendable. Residual failure: retrieve can still return two issuers
while the extractive quotes miss one keyword (`climate` vs `medical`).
Keyword metric uses answer **or** chunk haystack, so this can hide a
thin answer.

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
questions (q013, q025, q032) will look like two bullets, not a contrast.
That is acceptable for Week 2. Week 3 LangGraph + Grok should still be
gated: uncited synthesis is refused.

### F8. Citation index vs payload identity

Citations are 1-based positions in the **retrieved list**, not stable
chunk IDs in the prose. If rerank reorders the pool, `[1]` points at a
different chunk. Footer includes `chunk_id` so the UI can show the real
span. Do not grade citation accuracy by index alone in later evals.

## 3. Priority fixes (do not expand scope)

1. Persist `evals/results/latest.json` from `make eval` once a writable
   checkout runs the harness (numbers will still be demo until ingest).
2. After first live catalog: re-run the 34 and tag each residual miss
   as retrieve / filter / refuse-policy / generation.
3. Add gold numeric spans for q016/q030-class items (Week 3 metrics).
4. Consider requiring **all** named tickers in the citation set, not just
   retrieve payloads, for multi-ticker items.
5. Do not raise chunk size or swap embedders based on demo scores.

## 4. Demo metric contract (regression guard)

From `tests/test_eval.py`:

- `n >= 30` questions loaded
- at least one `expect_refuse` and one `out_of_corpus` / `multi_ticker`
- demo composite `> 0.5`
- q015 and q029 refuse
- q001 answers with citations and a `Sources:` footer

If composite collapses below 0.5, the refuse policy or demo corpus
regressed. Do not "fix" it by deleting hard questions.
