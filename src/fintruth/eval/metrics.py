"""Eval metrics: refusal, citations, keywords, numerical support."""

from __future__ import annotations

import re
from dataclasses import dataclass

from fintruth.eval.dataset import EvalQuestion
from fintruth.generation.chain import GroundedAnswer

# Captures 201, 1,234.5, 12%, $201 — used for numerical faithfulness.
_NUMBER = re.compile(r"(?<!\w)(?:\$)?(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)%?(?!\w)")


@dataclass(slots=True)
class ItemScore:
    """Per-question binary checks plus a 0–1 composite."""

    question_id: str
    refusal_ok: bool
    citation_ok: bool
    keyword_ok: bool
    ticker_ok: bool
    numerical_ok: bool
    citation_support_ok: bool
    composite: float


def normalize_number(token: str) -> str:
    """Strip currency/percent/commas so '201' matches '$201 billion'."""
    cleaned = token.strip().lower().replace(",", "").replace("$", "").replace("%", "")
    try:
        value = float(cleaned)
    except ValueError:
        return cleaned
    if value.is_integer():
        return str(int(value))
    return format(value, "g")


def extract_numbers(text: str) -> set[str]:
    """Return normalized numeric tokens found in ``text``."""
    return {normalize_number(m.group(1)) for m in _NUMBER.finditer(text or "")}


def _cited_chunk_texts(result: GroundedAnswer) -> str:
    texts: list[str] = []
    for cite in result.citations:
        if 1 <= cite.index <= len(result.chunks):
            texts.append(result.chunks[cite.index - 1].text)
    return " ".join(texts)


def _cited_haystack(result: GroundedAnswer) -> str:
    """Answer + *cited* chunks only — uncited retrieve hits cannot inflate keywords."""
    return " ".join([result.answer, _cited_chunk_texts(result)]).lower()


def _citation_indexes_valid(result: GroundedAnswer) -> bool:
    n = len(result.chunks)
    if not result.citations:
        return True
    return all(1 <= c.index <= n for c in result.citations)


def score_keywords(question: EvalQuestion, result: GroundedAnswer) -> bool:
    """Keywords must appear in the answer or the cited spans.

    Multi-ticker items with two or more gold keywords require *all* of them so a
    one-sided contrast cannot pass on a word that only lives in an uncited hit.
    """
    if question.expect_refuse or not question.keywords:
        return True
    blob = _cited_haystack(result)
    needles = [k.lower() for k in question.keywords]
    if question.category == "multi_ticker" and len(needles) >= 2:
        return all(k in blob for k in needles)
    return any(k in blob for k in needles)


def score_numerical(question: EvalQuestion, result: GroundedAnswer) -> bool:
    """Gold numbers must appear in the answer and in cited evidence.

    ``numerical_absent`` items pass only when the system refuses or emits no
    standalone figures (no invented unit volumes).
    """
    if question.expect_refuse or question.category == "numerical_absent":
        if result.refused:
            return True
        return not extract_numbers(result.answer)

    expected = [normalize_number(n) for n in question.expected_numbers]
    if not expected:
        return True
    answer_nums = extract_numbers(result.answer)
    evidence = _cited_chunk_texts(result) or " ".join(c.text for c in result.chunks)
    evidence_nums = extract_numbers(evidence)
    return all(n in answer_nums and n in evidence_nums for n in expected)


def score_citation_support(question: EvalQuestion, result: GroundedAnswer) -> bool:
    """Citations must be in-range and ticker-aligned with the question."""
    if question.expect_refuse:
        return True
    if question.must_cite and not result.citations:
        return False
    if not _citation_indexes_valid(result):
        return False
    wanted = {t.upper() for t in question.tickers}
    if not wanted or not result.citations:
        return True
    cited = {c.ticker.upper() for c in result.citations if c.ticker}
    if not (cited & wanted) or not cited <= wanted:
        return False
    # Comparison items must cite every named issuer, not just retrieve them.
    if len(wanted) >= 2 and question.category == "multi_ticker":
        return wanted <= cited
    return True


def score_item(question: EvalQuestion, result: GroundedAnswer) -> ItemScore:
    """Score one generate_answer result against gold flags."""
    refusal_ok = result.refused is question.expect_refuse

    if question.expect_refuse:
        citation_ok = True
        keyword_ok = True
        ticker_ok = True
    else:
        citation_ok = (not question.must_cite) or bool(result.citations)
        keyword_ok = score_keywords(question, result)
        cited_tickers = {c.ticker.upper() for c in result.citations if c.ticker}
        hit_tickers = {str(c.payload.get("ticker", "")).upper() for c in result.chunks}
        wanted = {t.upper() for t in question.tickers}
        ticker_ok = not wanted or bool(wanted & (cited_tickers | hit_tickers))
        if len(wanted) >= 2 and question.category == "multi_ticker":
            ticker_ok = wanted <= cited_tickers

    numerical_ok = score_numerical(question, result)
    citation_support_ok = score_citation_support(question, result)

    flags = [
        refusal_ok,
        citation_ok,
        keyword_ok,
        ticker_ok,
        numerical_ok,
        citation_support_ok,
    ]
    composite = sum(1.0 for f in flags if f) / len(flags)
    return ItemScore(
        question_id=question.id,
        refusal_ok=refusal_ok,
        citation_ok=citation_ok,
        keyword_ok=keyword_ok,
        ticker_ok=ticker_ok,
        numerical_ok=numerical_ok,
        citation_support_ok=citation_support_ok,
        composite=composite,
    )


def summarize(scores: list[ItemScore]) -> dict[str, float]:
    """Mean rates across an eval run."""
    n = max(len(scores), 1)
    return {
        "n": float(len(scores)),
        "refusal_accuracy": sum(s.refusal_ok for s in scores) / n,
        "citation_accuracy": sum(s.citation_ok for s in scores) / n,
        "citation_support": sum(s.citation_support_ok for s in scores) / n,
        "keyword_hit_rate": sum(s.keyword_ok for s in scores) / n,
        "ticker_hit_rate": sum(s.ticker_ok for s in scores) / n,
        "numerical_accuracy": sum(s.numerical_ok for s in scores) / n,
        "composite": sum(s.composite for s in scores) / n,
    }
