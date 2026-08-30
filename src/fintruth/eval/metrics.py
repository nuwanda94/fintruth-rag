"""Minimal Week 1 metrics: refusal agreement, citations, keyword coverage."""

from __future__ import annotations

from dataclasses import dataclass

from fintruth.eval.dataset import EvalQuestion
from fintruth.generation.chain import GroundedAnswer


@dataclass(slots=True)
class ItemScore:
    """Per-question binary checks plus a 0–1 composite."""

    question_id: str
    refusal_ok: bool
    citation_ok: bool
    keyword_ok: bool
    ticker_ok: bool
    composite: float


def _haystack(result: GroundedAnswer) -> str:
    parts = [result.answer]
    parts.extend(c.text for c in result.chunks)
    return " ".join(parts).lower()


def score_item(question: EvalQuestion, result: GroundedAnswer) -> ItemScore:
    """Score one generate_answer result against gold flags."""
    refusal_ok = result.refused is question.expect_refuse

    if question.expect_refuse:
        citation_ok = True
        keyword_ok = True
        ticker_ok = True
    else:
        citation_ok = (not question.must_cite) or bool(result.citations)
        blob = _haystack(result)
        keyword_ok = not question.keywords or any(k in blob for k in question.keywords)
        cited_tickers = {c.ticker.upper() for c in result.citations if c.ticker}
        hit_tickers = {str(c.payload.get("ticker", "")).upper() for c in result.chunks}
        wanted = {t.upper() for t in question.tickers}
        ticker_ok = not wanted or bool(wanted & (cited_tickers | hit_tickers))

    flags = [refusal_ok, citation_ok, keyword_ok, ticker_ok]
    composite = sum(1.0 for f in flags if f) / len(flags)
    return ItemScore(
        question_id=question.id,
        refusal_ok=refusal_ok,
        citation_ok=citation_ok,
        keyword_ok=keyword_ok,
        ticker_ok=ticker_ok,
        composite=composite,
    )


def summarize(scores: list[ItemScore]) -> dict[str, float]:
    """Mean rates across an eval run."""
    n = max(len(scores), 1)
    return {
        "n": float(len(scores)),
        "refusal_accuracy": sum(s.refusal_ok for s in scores) / n,
        "citation_accuracy": sum(s.citation_ok for s in scores) / n,
        "keyword_hit_rate": sum(s.keyword_ok for s in scores) / n,
        "ticker_hit_rate": sum(s.ticker_ok for s in scores) / n,
        "composite": sum(s.composite for s in scores) / n,
    }
