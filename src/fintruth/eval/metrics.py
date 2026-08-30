"""Eval metrics: refusal, citations, keywords, numerical support."""

from __future__ import annotations

import re
from dataclasses import dataclass

from fintruth.eval.dataset import EvalQuestion
from fintruth.generation.chain import Citation, GroundedAnswer
from fintruth.retrieval.hybrid import RetrievedChunk

# Captures 201, 1,234.5, 12%, $201 — used for numerical faithfulness.
_NUMBER = re.compile(r"(?<!\w)(?:\$)?(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)%?(?!\w)")

_SCALE_WORDS = (
    "trillion",
    "billion",
    "million",
    "thousand",
    "percent",
    "units",
    "unit",
    "pct",
    "bn",
)
_SCALE_ALIAS = {
    "trillion": "trillion",
    "billion": "billion",
    "bn": "billion",
    "million": "million",
    "thousand": "thousand",
    "percent": "percent",
    "pct": "percent",
    "unit": "unit",
    "units": "unit",
}
_QUANTITY = re.compile(
    r"(?<!\w)(?P<currency>\$)?(?P<num>\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)"
    r"(?P<pct>%)?(?:\s*(?P<scale>trillion|billion|million|thousand|percent|units?|pct|bn))?",
    re.I,
)


@dataclass(frozen=True, slots=True)
class Quantity:
    """A numeric mention plus an optional magnitude / unit scale."""

    mantissa: str
    scale: str | None = None


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


def parse_quantity(token: str) -> Quantity:
    """Parse a gold or raw token such as '201 billion' or '$201'."""
    raw = (token or "").strip().lower()
    match = _QUANTITY.search(raw)
    if not match:
        return Quantity(mantissa=normalize_number(raw), scale=None)
    scale_raw = match.group("scale")
    if match.group("pct"):
        scale = "percent"
    elif scale_raw:
        scale = _SCALE_ALIAS.get(scale_raw.lower())
    else:
        scale = None
        for word in _SCALE_WORDS:
            if re.search(rf"\b{word}\b", raw):
                scale = _SCALE_ALIAS[word]
                break
    return Quantity(mantissa=normalize_number(match.group("num")), scale=scale)


def extract_quantities(text: str) -> list[Quantity]:
    """Extract number+scale mentions from prose (eval-side unit parser)."""
    out: list[Quantity] = []
    for match in _QUANTITY.finditer(text or ""):
        scale_raw = match.group("scale")
        if match.group("pct"):
            scale = "percent"
        elif scale_raw:
            scale = _SCALE_ALIAS.get(scale_raw.lower())
        else:
            scale = None
        out.append(Quantity(mantissa=normalize_number(match.group("num")), scale=scale))
    return out


def quantities_cover(gold: Quantity, observed: list[Quantity]) -> bool:
    """True when some observed mention matches gold mantissa and scale.

    A gold token without a scale still matches any magnitude (legacy '201').
    A gold token *with* a scale must see that same scale — '$201 billion'
    cannot satisfy '201 million' unit volume.
    """
    for item in observed:
        if item.mantissa != gold.mantissa:
            continue
        if gold.scale is None or item.scale == gold.scale:
            return True
    return False


def resolve_cited_chunk(result: GroundedAnswer, cite: Citation) -> RetrievedChunk | None:
    """Map a citation onto a retrieve hit by stable chunk_id, then index.

    Prose markers stay 1-based list positions, but rerank can reorder the
    pool after parse. Keyword / numerical checks must follow ``chunk_id``
    so ``[1]`` after a shuffle does not silently score a different span.
    """
    if cite.chunk_id:
        for chunk in result.chunks:
            if chunk.chunk_id == cite.chunk_id:
                return chunk
    if 1 <= cite.index <= len(result.chunks):
        return result.chunks[cite.index - 1]
    return None


def _cited_chunk_texts(result: GroundedAnswer) -> str:
    texts: list[str] = []
    for cite in result.citations:
        chunk = resolve_cited_chunk(result, cite)
        if chunk is not None:
            texts.append(chunk.text)
    return " ".join(texts)


def _cited_haystack(result: GroundedAnswer) -> str:
    """Answer + *cited* chunks only — uncited retrieve hits cannot inflate keywords."""
    return " ".join([result.answer, _cited_chunk_texts(result)]).lower()


def _cited_texts_by_ticker(result: GroundedAnswer) -> dict[str, str]:
    """Cited span text keyed by citation ticker (payload fallback)."""
    buckets: dict[str, list[str]] = {}
    for cite in result.citations:
        chunk = resolve_cited_chunk(result, cite)
        if chunk is None:
            continue
        ticker = (cite.ticker or str(chunk.payload.get("ticker", ""))).upper()
        if not ticker:
            continue
        buckets.setdefault(ticker, []).append(chunk.text)
    return {ticker: " ".join(texts).lower() for ticker, texts in buckets.items()}


def _citations_resolve(result: GroundedAnswer) -> bool:
    """Every citation must land on a retrieve hit (id first, then index)."""
    if not result.citations:
        return True
    known_ids = {c.chunk_id for c in result.chunks}
    for cite in result.citations:
        if resolve_cited_chunk(result, cite) is None:
            return False
        # Stale id after a pool swap is a support failure even if index is in range.
        if cite.chunk_id and cite.chunk_id not in known_ids:
            return False
    return True


def score_keywords(question: EvalQuestion, result: GroundedAnswer) -> bool:
    """Keywords must appear in the answer or the cited spans.

    Multi-ticker items with two or more gold keywords require *all* of them so a
    one-sided contrast cannot pass on a word that only lives in an uncited hit.

    When ``keywords_by_ticker`` is set, each issuer's needles must appear in
    *that issuer's cited spans* so "revenue" on AAPL cannot satisfy MSFT.
    """
    if question.expect_refuse:
        return True
    per_issuer = {
        ticker.upper(): [k.lower() for k in needles]
        for ticker, needles in (question.keywords_by_ticker or {}).items()
        if needles
    }
    if question.category == "multi_ticker" and per_issuer:
        cited = _cited_texts_by_ticker(result)
        for ticker, needles in per_issuer.items():
            blob = cited.get(ticker, "")
            if not all(k in blob for k in needles):
                return False
        return True
    if not question.keywords:
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

    Gold tokens may carry a scale (``201 billion``). When they do, a nearby
    figure with the same mantissa but a different magnitude does not count.
    """
    if question.expect_refuse or question.category == "numerical_absent":
        if result.refused:
            return True
        return not extract_numbers(result.answer)

    expected = [parse_quantity(n) for n in question.expected_numbers]
    if not expected:
        return True
    answer_qs = extract_quantities(result.answer)
    evidence = _cited_chunk_texts(result) or " ".join(c.text for c in result.chunks)
    evidence_qs = extract_quantities(evidence)
    return all(
        quantities_cover(gold, answer_qs) and quantities_cover(gold, evidence_qs)
        for gold in expected
    )


def score_citation_support(question: EvalQuestion, result: GroundedAnswer) -> bool:
    """Citations must resolve to retrieve hits and stay ticker-aligned."""
    if question.expect_refuse:
        return True
    if question.must_cite and not result.citations:
        return False
    if not _citations_resolve(result):
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
