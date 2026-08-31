"""Exact-figure asks need the year near a quantity, not a distant mention."""

from fintruth.generation.chain import generate_answer, should_refuse
from fintruth.generation.refuse import evidence_has_year_near_quantity
from fintruth.generation.units import UNIT_QUANTITY_RE
from fintruth.retrieval.hybrid import RetrievedChunk


def _chunk(chunk_id: str, text: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        text=text,
        score=0.2,
        dense_rank=1,
        sparse_rank=None,
        payload={
            "ticker": "AAPL",
            "form": "10-K",
            "section": "mda",
            "filing_date": "2024-11-01",
        },
    )


QUESTION = "What was Apple's exact FY2012 Greater China iPhone unit volume?"


def test_year_far_from_quantity_is_not_period_evidence() -> None:
    distant = _chunk(
        "AAPL:mda:distant",
        "In 2012 we opened a Greater China retail store. "
        + ("Competition intensified. " * 8)
        + "iPhone net sales were $201 billion for fiscal 2024.",
    )
    assert not evidence_has_year_near_quantity([distant], ["2012"])
    reason = should_refuse([distant], QUESTION)
    assert reason is not None
    assert "not near a quantity" in reason


def test_year_next_to_unit_quantity_passes_period_gate() -> None:
    near = _chunk(
        "AAPL:mda:near",
        "Greater China iPhone unit volume was 26 million in fiscal 2012.",
    )
    assert evidence_has_year_near_quantity([near], ["2012"])
    assert evidence_has_year_near_quantity(
        [near], ["2012"], quantity_re=UNIT_QUANTITY_RE
    )
    assert should_refuse([near], QUESTION) is None
    result = generate_answer(QUESTION, [near], use_llm=False)
    assert not result.refused


def test_bare_year_is_not_treated_as_a_quantity() -> None:
    only_year = _chunk(
        "AAPL:mda:year",
        "The 2012 Form 10-K discusses Greater China iPhone competition.",
    )
    assert not evidence_has_year_near_quantity([only_year], ["2012"])


def test_year_next_to_dollars_does_not_satisfy_unit_ask() -> None:
    """F2 residual: 2012 revenue plus later units is the wrong figure."""
    mixed = _chunk(
        "AAPL:mda:mixed",
        "In fiscal 2012 Greater China iPhone net sales were $22.8 billion. "
        + ("Retail stores expanded. " * 6)
        + "Unit volume was 232 million units in fiscal 2024.",
    )
    assert evidence_has_year_near_quantity([mixed], ["2012"])
    assert not evidence_has_year_near_quantity(
        [mixed], ["2012"], quantity_re=UNIT_QUANTITY_RE
    )
    reason = should_refuse([mixed], QUESTION)
    assert reason is not None
    assert "not near a unit quantity" in reason
    result = generate_answer(QUESTION, [mixed], use_llm=False)
    assert result.refused
