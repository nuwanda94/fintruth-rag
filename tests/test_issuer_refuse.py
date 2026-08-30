"""Issuer-aware refusal: named companies missing from hits must refuse."""

from fintruth.generation.chain import mentioned_tickers, should_refuse
from fintruth.retrieval.hybrid import RetrievedChunk


def test_tesla_name_maps_to_tsla() -> None:
    assert "TSLA" in mentioned_tickers("Did Tesla disclose Cybertruck unit deliveries?")


def test_should_refuse_missing_named_issuer() -> None:
    chunk = RetrievedChunk(
        chunk_id="AAPL:risk:0",
        text="Apple faces intense competition.",
        score=0.05,
        dense_rank=1,
        sparse_rank=1,
        payload={"ticker": "AAPL", "form": "10-K", "section": "risk_factors", "filing_date": "2024-11-01"},
    )
    reason = should_refuse([chunk], "What litigation contingencies did Tesla disclose in 2019?")
    assert reason is not None
    assert "TSLA" in reason
