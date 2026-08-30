"""Offline tests for lexical rerank, as-of filters, and ablations."""

from fintruth.indexing.embedder import HashEmbedder
from fintruth.indexing.qdrant_store import InMemoryVectorStore, index_payloads
from fintruth.retrieval.compare import compare_retrievers
from fintruth.retrieval.filters import RetrievalFilters
from fintruth.retrieval.hybrid import HybridRetriever, RetrievedChunk
from fintruth.retrieval.reranker import LexicalReranker


def _payloads() -> list[dict]:
    return [
        {
            "chunk_id": "AAPL:2020:risk_factors:0",
            "text": "Apple historically noted some competitive pressure in hardware.",
            "ticker": "AAPL",
            "form": "10-K",
            "filing_date": "2020-10-30",
            "section": "risk_factors",
        },
        {
            "chunk_id": "AAPL:2024:risk_factors:0",
            "text": "Apple faces intense competition in smartphones and services.",
            "ticker": "AAPL",
            "form": "10-K",
            "filing_date": "2024-11-01",
            "section": "risk_factors",
        },
        {
            "chunk_id": "AAPL:2024:mda:0",
            "text": "iPhone revenue increased year over year driven by services mix.",
            "ticker": "AAPL",
            "form": "10-K",
            "filing_date": "2024-11-01",
            "section": "mda",
        },
        {
            "chunk_id": "XOM:2024:risk_factors:0",
            "text": "ExxonMobil commodity prices and refining margins remain volatile.",
            "ticker": "XOM",
            "form": "10-K",
            "filing_date": "2024-02-28",
            "section": "risk_factors",
        },
    ]


def test_lexical_reranker_prefers_competition_risk_chunk() -> None:
    chunks = [
        RetrievedChunk(
            chunk_id="mda",
            text="iPhone revenue increased year over year driven by services mix.",
            score=0.02,
            dense_rank=1,
            sparse_rank=2,
            payload={"section": "mda", "filing_date": "2024-11-01"},
        ),
        RetrievedChunk(
            chunk_id="risk",
            text="Apple faces intense competition in smartphones and services.",
            score=0.015,
            dense_rank=2,
            sparse_rank=1,
            payload={"section": "risk_factors", "filing_date": "2024-11-01"},
        ),
    ]
    ranked = LexicalReranker().rerank("What competition risks does Apple disclose?", chunks, top_k=2)
    assert ranked[0].chunk_id == "risk"
    assert ranked[0].rerank_score is not None
    assert ranked[0].rerank_score >= ranked[1].rerank_score  # type: ignore[operator]


def test_as_of_filter_drops_later_filings() -> None:
    payloads = _payloads()
    store = InMemoryVectorStore()
    embedder = HashEmbedder(dim=64)
    index_payloads(payloads, embedder=embedder, store=store)
    retriever = HybridRetriever(store=store, embedder=embedder)
    retriever.add_sparse_corpus(payloads)
    hits = retriever.retrieve(
        "Apple competition",
        filters=RetrievalFilters(tickers=["AAPL"], as_of="2021-12-31"),
        final_k=5,
        rerank=False,
    )
    assert hits
    assert all(h.payload["filing_date"] <= "2021-12-31" for h in hits)
    assert all(h.payload["chunk_id"].startswith("AAPL:2020") for h in hits)


def test_compare_retrievers_returns_three_arms() -> None:
    payloads = _payloads()
    store = InMemoryVectorStore()
    embedder = HashEmbedder(dim=64)
    index_payloads(payloads, embedder=embedder, store=store)
    retriever = HybridRetriever(store=store, embedder=embedder)
    retriever.add_sparse_corpus(payloads)
    arms = compare_retrievers(
        retriever,
        "What competition risks does Apple disclose?",
        filters=RetrievalFilters(tickers=["AAPL"]),
        final_k=3,
    )
    assert [a.name for a in arms] == ["dense", "hybrid", "hybrid+rerank"]
    rerank_arm = arms[2]
    assert rerank_arm.traces is not None
    assert rerank_arm.traces.reranked is True
    assert rerank_arm.traces.latency_ms >= 0.0
    assert rerank_arm.hits[0].chunk_id == "AAPL:2024:risk_factors:0"
