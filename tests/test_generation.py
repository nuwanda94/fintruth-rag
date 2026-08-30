"""Offline tests for citation parse, refusal, and extractive grounding."""

from fintruth.generation.chain import (
    generate_answer,
    mentioned_tickers,
    parse_citations,
    should_refuse,
)
from fintruth.generation.prompts import REFUSAL_PREFIX, build_messages, format_evidence_block
from fintruth.indexing.embedder import HashEmbedder
from fintruth.indexing.qdrant_store import InMemoryVectorStore, index_payloads
from fintruth.retrieval.filters import RetrievalFilters
from fintruth.retrieval.hybrid import HybridRetriever, RetrievedChunk


def _chunk(chunk_id: str, text: str, **meta: str) -> RetrievedChunk:
    payload = {
        "text": text,
        "ticker": meta.get("ticker", "AAPL"),
        "form": meta.get("form", "10-K"),
        "section": meta.get("section", "risk_factors"),
        "filing_date": meta.get("filing_date", "2024-11-01"),
    }
    return RetrievedChunk(
        chunk_id=chunk_id,
        text=text,
        score=meta.get("score") and float(meta["score"]) or 0.05,  # type: ignore[arg-type]
        dense_rank=1,
        sparse_rank=1,
        payload=payload,
    )


def test_parse_citations_maps_one_indexed_markers() -> None:
    chunks = [
        _chunk("a", "Apple faces competition."),
        _chunk("b", "iPhone revenue increased."),
    ]
    cites = parse_citations("Competition is disclosed [1] and revenue rose [2][1].", chunks)
    assert [c.index for c in cites] == [1, 2]
    assert cites[0].chunk_id == "a"
    assert cites[1].chunk_id == "b"


def test_should_refuse_on_empty_and_low_score() -> None:
    assert should_refuse([], "anything") == "no retrieved evidence"
    weak = [_chunk("a", "unrelated filing boilerplate")]
    weak[0].score = 0.001
    reason = should_refuse(weak, "Apple competition risks")
    assert reason is not None
    assert "score" in reason or "overlap" in reason


def test_extractive_answer_cites_overlapping_chunk() -> None:
    chunks = [
        _chunk("AAPL:risk:0", "Apple faces intense competition in smartphones."),
        _chunk("XOM:risk:0", "Commodity prices remain volatile.", ticker="XOM"),
    ]
    result = generate_answer("What competition risks does Apple disclose?", chunks, use_llm=False)
    assert not result.refused
    assert "[1]" in result.answer
    assert result.citations
    assert result.citations[0].chunk_id == "AAPL:risk:0"
    assert "Sources:" in result.answer
    assert "AAPL 10-K risk_factors" in result.answer


def test_extractive_refusal_when_no_term_overlap() -> None:
    chunks = [_chunk("a", "Quarterly cash dividend declared by the board.")]
    result = generate_answer("What litigation contingencies did Tesla disclose?", chunks, use_llm=False)
    assert result.refused
    assert result.answer.startswith(REFUSAL_PREFIX)


def test_multi_ticker_refuses_when_one_name_missing() -> None:
    chunks = [_chunk("AAPL:risk:0", "Apple faces intense competition.")]
    result = generate_answer(
        "Compare AAPL competition with MSFT cloud competition.",
        chunks,
        use_llm=False,
    )
    assert result.refused
    assert "MSFT" in (result.refusal_reason or "")


def test_mentioned_tickers_dedupes() -> None:
    assert mentioned_tickers("AAPL vs MSFT vs AAPL") == ["AAPL", "MSFT"]


def test_llm_mode_parses_refusal_prefix() -> None:
    chunks = [_chunk("a", "Apple faces intense competition.")]
    result = generate_answer(
        "question",
        chunks,
        model_text="REFUSAL: evidence does not address the period asked",
    )
    assert result.refused
    assert result.mode == "llm"
    assert "period" in (result.refusal_reason or "")


def test_llm_mode_refuses_uncited_claims() -> None:
    chunks = [_chunk("a", "Apple faces intense competition.")]
    result = generate_answer(
        "What competition risks does Apple disclose?",
        chunks,
        model_text="Apple faces intense competition in every market.",
    )
    assert result.refused
    assert result.refusal_reason == "model answer lacked citations"


def test_llm_mode_attaches_sources_footer() -> None:
    chunks = [_chunk("a", "Apple faces intense competition.")]
    result = generate_answer(
        "What competition risks does Apple disclose?",
        chunks,
        model_text="Apple discloses intense competition [1].",
    )
    assert not result.refused
    assert result.mode == "llm"
    assert "Sources:" in result.answer
    assert result.citations[0].ticker == "AAPL"


def test_prompt_includes_numbered_evidence() -> None:
    chunks = [_chunk("a", "Apple faces intense competition.")]
    block = format_evidence_block(chunks)
    assert "[1]" in block
    assert "AAPL" in block
    messages = build_messages("competition risks", chunks)
    assert messages[0]["role"] == "system"
    assert "Evidence:" in messages[1]["content"]


def test_end_to_end_retrieve_then_generate() -> None:
    payloads = [
        {
            "chunk_id": "AAPL:acc:risk_factors:0",
            "text": "Apple faces intense competition in smartphones and services.",
            "ticker": "AAPL",
            "form": "10-K",
            "filing_date": "2024-11-01",
            "section": "risk_factors",
        },
        {
            "chunk_id": "XOM:acc:risk_factors:0",
            "text": "ExxonMobil commodity prices and refining margins remain volatile.",
            "ticker": "XOM",
            "form": "10-K",
            "filing_date": "2024-02-28",
            "section": "risk_factors",
        },
    ]
    store = InMemoryVectorStore()
    embedder = HashEmbedder(dim=64)
    index_payloads(payloads, embedder=embedder, store=store)
    retriever = HybridRetriever(store=store, embedder=embedder)
    retriever.add_sparse_corpus(payloads)
    hits = retriever.retrieve(
        "What competition risks does Apple disclose?",
        filters=RetrievalFilters(tickers=["AAPL"]),
        final_k=2,
    )
    result = generate_answer("What competition risks does Apple disclose?", hits, use_llm=False)
    assert hits
    assert not result.refused
    assert result.citations
