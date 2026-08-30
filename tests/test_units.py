"""Unit-volume generation gate and scale-aware numerical scoring."""

from fintruth.eval.dataset import EvalQuestion
from fintruth.eval.metrics import extract_quantities, parse_quantity, quantities_cover, score_item
from fintruth.generation.chain import Citation, GroundedAnswer, generate_answer
from fintruth.generation.units import asks_unit_volume, evidence_has_unit_quantity
from fintruth.retrieval.hybrid import RetrievedChunk


def _chunk(chunk_id: str, text: str, ticker: str = "AAPL", **payload: str) -> RetrievedChunk:
    data = {"ticker": ticker, "form": "10-K", "section": "mda", "filing_date": "2024-11-01"}
    data.update(payload)
    return RetrievedChunk(
        chunk_id=chunk_id,
        text=text,
        score=0.2,
        dense_rank=1,
        sparse_rank=None,
        payload=data,
    )


def test_quantity_parser_distinguishes_scale() -> None:
    gold_bn = parse_quantity("201 billion")
    observed = extract_quantities("iPhone net sales were $201 billion for fiscal 2024.")
    assert gold_bn.scale == "billion"
    assert quantities_cover(gold_bn, observed)
    assert quantities_cover(parse_quantity("201"), observed)
    assert not quantities_cover(parse_quantity("201 million"), observed)


def test_numerical_score_requires_matching_scale() -> None:
    q = EvalQuestion(
        id="units",
        question="What was Apple iPhone unit volume?",
        tickers=["AAPL"],
        expected_numbers=["26 million"],
    )
    dollar = _chunk("AAPL:mda", "iPhone net sales were $201 billion for fiscal 2024.")
    leaked = GroundedAnswer(
        question=q.question,
        answer="iPhone net sales were $201 billion [1]",
        refused=False,
        refusal_reason=None,
        citations=[Citation(1, dollar.chunk_id, "AAPL", "10-K", "mda", "2024-11-01")],
        chunks=[dollar],
    )
    assert not score_item(q, leaked).numerical_ok
    units = _chunk("AAPL:mda2", "Greater China iPhone unit volume was 26 million in fiscal 2012.")
    good = GroundedAnswer(
        question=q.question,
        answer="Greater China iPhone unit volume was 26 million [1]",
        refused=False,
        refusal_reason=None,
        citations=[Citation(1, units.chunk_id, "AAPL", "10-K", "mda", "2024-11-01")],
        chunks=[units],
    )
    assert score_item(q, good).numerical_ok


def test_exact_figure_refuses_revenue_when_units_asked() -> None:
    assert asks_unit_volume("What was Apple's exact FY2012 greater-China iPhone unit volume?")
    chunks = [_chunk("AAPL:mda:2012", "iPhone net sales were $201 billion in fiscal 2012.")]
    assert not evidence_has_unit_quantity(chunks)
    result = generate_answer(
        "What was Apple's exact FY2012 greater-China iPhone unit volume?",
        chunks,
        use_llm=False,
    )
    assert result.refused
    assert "unit volume" in (result.refusal_reason or "")
