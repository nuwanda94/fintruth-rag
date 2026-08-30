"""Offline tests for hashing embedder + hybrid RRF retrieval."""

from fintruth.indexing.embedder import HashEmbedder
from fintruth.indexing.qdrant_store import InMemoryVectorStore, index_payloads
from fintruth.retrieval.filters import RetrievalFilters
from fintruth.retrieval.hybrid import HybridRetriever


def _payloads() -> list[dict]:
    return [
        {
            "chunk_id": "AAPL:acc:risk_factors:0",
            "text": "Apple faces intense competition in smartphones and services.",
            "ticker": "AAPL",
            "form": "10-K",
            "filing_date": "2024-11-01",
            "section": "risk_factors",
        },
        {
            "chunk_id": "AAPL:acc:mda:0",
            "text": "iPhone revenue increased year over year driven by services mix.",
            "ticker": "AAPL",
            "form": "10-K",
            "filing_date": "2024-11-01",
            "section": "mda",
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


def test_hash_embedder_is_deterministic() -> None:
    emb = HashEmbedder(dim=64)
    a = emb.embed_query("liquidity and capital resources")
    b = emb.embed_query("liquidity and capital resources")
    assert a == b
    assert len(a) == 64
    assert abs(sum(x * x for x in a) - 1.0) < 1e-6


def test_hybrid_retriever_ranks_relevant_ticker() -> None:
    payloads = _payloads()
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
    assert hits
    assert all(h.payload["ticker"] == "AAPL" for h in hits)
    assert any("competition" in h.text.lower() for h in hits)


def test_section_filter_excludes_mda() -> None:
    payloads = _payloads()
    store = InMemoryVectorStore()
    embedder = HashEmbedder(dim=64)
    index_payloads(payloads, embedder=embedder, store=store)
    retriever = HybridRetriever(store=store, embedder=embedder)
    retriever.add_sparse_corpus(payloads)
    hits = retriever.retrieve(
        "revenue increased",
        filters=RetrievalFilters(tickers=["AAPL"], sections=["risk_factors"]),
        final_k=5,
    )
    assert all(h.payload["section"] == "risk_factors" for h in hits)
