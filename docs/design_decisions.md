# Design Decisions

Interview-facing log of choices that are actually in the repo today.
Evidence is from code + the offline demo eval harness (`DEMO_CORPUS`,
`evals/questions.jsonl`, `tests/test_eval.py`). Live SEC catalog numbers
are still blocked on ingest credentials, so no quality claims are made
from hash embeddings.

## D1. Offline-first loop before live vendors

**Choice.** Hash embedder, in-memory vector store, in-process BM25, lexical
reranker, extractive generation. Vendor hooks exist (`XAI_API_KEY`,
`COHERE_API_KEY`, Qdrant URL) but are not required for tests.

**Alternatives.** Voyage / OpenAI embeddings + Cohere rerank + Grok from day one.

**Why.** Interview-max needs a loop you can run and debug without keys.
Swap points stay typed (`Embedder`, `VectorStore`, `Reranker`,
`generate_answer(use_llm=...)`).

**Cost.** Demo ablation ranks are wiring scores, not retrieval quality.
Document that in every metric table.

## D2. Section-aware chunks with filing metadata, not naive page windows

**Choice.** Parse MD&A / Risk Factors / notes, then paragraph-merge into
~512-token windows with 64-token overlap. Payload always carries
`ticker`, `form`, `filing_date`, `section`, `accession`, `chunk_id`.

**Alternatives.** Fixed-character sliding windows; parent-document;
full-document embeddings.

**Why.** SEC questions are almost always section- and issuer-scoped.
Metadata filters are cheaper and more reliable than hoping the embedder
separates AAPL MD&A from MSFT risk factors.

**Open.** Chunk size not yet tuned on live filings. Parent-document is
explicitly out of scope unless Week 3 buffer remains.

## D3. Hybrid dense + sparse with Reciprocal Rank Fusion

**Choice.** Dense kNN + BM25-ish sparse, fused with RRF (`k=60`), then
optional rerank of a pool (`RERANK_POOL_K=24`) down to `retrieve_final_k=8`.
Modes `dense | sparse | hybrid` exist for ablation (`scripts/ask.py --compare`).

**Alternatives.** Dense-only; sparse-only; weighted score sum instead of RRF.

**Why.** RRF needs no score calibration across heterogeneous rankers.
Finance queries mix exact tokens ("Azure", "iPhone", "goodwill") with
paraphrase ("medical cost trends").

**Evidence so far.** Unit tests show fusion + filters work on the demo
corpus. Do not cite demo nDCG as a quality result.

## D4. Lexical reranker as a protocol stand-in

**Choice.** `LexicalReranker`: Jaccard overlap + fused-score weight +
section hint + weak recency prior. `IdentityReranker` for naive arms.
`build_reranker` ignores Cohere even if a key is set, so eval stays
deterministic.

**Alternatives.** Call Cohere / BGE-reranker immediately.

**Why.** Same `Reranker` protocol either way. Recency prior is small
(`0.08 * (year-2020)/6`) so it cannot override lexical mismatch.

**Risk.** Section hints can over-promote Risk Factors when the query
contains "risk" even if MD&A is the right home. Watch this on live eval.

## D5. Point-in-time `as_of` is a hard cutoff, not a soft rank bias

**Choice.** `RetrievalFilters.as_of` tightens `date_to`. Later filings
are dropped, not down-weighted.

**Alternatives.** Recency boost only; dual index of "as-filed" vs "as-of".

**Why.** Financial research questions are often "what did the company
say as of date X". Mixing a later 10-K into that answer is a silent lie.

## D6. Extractive default + post-hoc citation / refusal gates

**Choice.** Default answer is quoted snippets with `[n]` markers and a
`Sources:` footer built from payload metadata. LLM path (Grok via stdlib
`urllib`) is optional and must still pass:

1. `should_refuse` (empty hits, low RRF score, no term overlap, missing
   ticker on multi-ticker questions)
2. model-emitted `REFUSAL:` prefix
3. at least one valid `[n]` citation, else refuse

Eval always forces `use_llm=False`.

**Alternatives.** Trust the model to cite; generate first and retrieve
second; allow uncited paraphrase.

**Why.** Truth-seeking demo is "show the chunk or refuse". Extractive
mode makes refusal tests deterministic. Uncited LLM text is treated as
a failure, not as a soft answer.

## D7. Refusal is a first-class label in the eval set

**Choice.** 34 questions. Categories include `risk`, `mda`, `multi_ticker`,
`out_of_corpus`, `numerical_absent`, `notes_sparse`. Gold flag
`expect_refuse` is scored as refusal accuracy.

**Alternatives.** Only answerable questions; LLM-as-judge only.

**Why.** A grounded system that never refuses will look fluent and still
be wrong on Tesla / BRK (not in demo corpus), 2012 unit volumes (not in
chunks), and notes/goodwill (section not ingested in the fixture).

## D8. Metrics are binary gates, not RAGAS yet

**Choice.** Per item: refusal agreement, citation present when required,
keyword hit in answer-or-chunks, ticker hit. Composite is the mean of
those four flags. Demo composite is asserted `> 0.5`.

**Alternatives.** RAGAS faithfulness / context precision from Week 1.

**Why.** RAGAS needs an LLM judge and a live corpus. Binary gates catch
the failure modes we actually designed (wrong refusal, missing cite,
wrong issuer). Custom numerical + citation-span checks are Week 3.

## D9. In-memory store until Qdrant earns its keep

**Choice.** `InMemoryVectorStore` implements the same search/filter
shape as the future Qdrant client. `qdrant_in_memory=True` by default.

**Why.** Hybrid + payload filters can be unit-tested in CI. Persistence
and server ops are out of interview-max until a real catalog exists.

## Decisions explicitly deferred (ROADMAP OUT)

- Agentic multi-hop / tool graphs beyond retrieve → grade → generate/refuse
- Parent-document and contextual compression
- XBRL / table understanding
- Cross-filing conflict detection
- Docker / multi-tenant production polish
