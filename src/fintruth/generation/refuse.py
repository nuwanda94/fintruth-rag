"""Issuer, period, and unit-volume refusal gates."""

from __future__ import annotations

import re

from fintruth.generation.citations import Citation
from fintruth.generation.segments import (
    evidence_has_year_near_segment,
    question_segments,
)
from fintruth.generation.units import (
    UNIT_QUANTITY_RE,
    asks_unit_volume,
    evidence_has_unit_quantity,
)
from fintruth.retrieval.hybrid import RetrievedChunk

_TOKEN = re.compile(r"[a-z0-9$%]+", re.I)
_TICKER = re.compile(
    r"\b(AAPL|MSFT|GOOGL|AMZN|META|NVDA|JPM|XOM|UNH|JNJ|TSLA|BRK)\b",
    re.I,
)
_YEAR = re.compile(r"\b(?:fy|fiscal\s+)?((?:19|20)\d{2})\b", re.I)
_EXACT_FACT = re.compile(
    r"\b(exact|unit volume|units?|deliveries|how many)\b",
    re.I,
)
# Dollar amounts, grouped thousands, or scaled counts — not bare years like 2012.
_FACT_QUANTITY = re.compile(
    r"\$\d[\d,]*(?:\.\d+)?"
    r"|\b\d{1,3}(?:,\d{3})+(?:\.\d+)?"
    r"|\b\d+(?:\.\d+)?\s*(?:thousand|million|billion)\b",
    re.I,
)

DEFAULT_MIN_SCORE = 0.012
DEFAULT_MIN_OVERLAP = 1
# Characters on either side of an asked year that must also contain a fact quantity.
YEAR_QUANTITY_WINDOW = 96

_NAME_TO_TICKER = {
    "TESLA": "TSLA",
    "APPLE": "AAPL",
    "MICROSOFT": "MSFT",
    "ALPHABET": "GOOGL",
    "GOOGLE": "GOOGL",
    "AMAZON": "AMZN",
    "META": "META",
    "FACEBOOK": "META",
    "NVIDIA": "NVDA",
    "JPMORGAN": "JPM",
    "EXXON": "XOM",
    "UNITEDHEALTH": "UNH",
    "JOHNSON": "JNJ",
    "BERKSHIRE": "BRK",
}


def mentioned_tickers(question: str) -> list[str]:
    """Tickers explicitly named in the question (interview-max universe)."""
    seen: list[str] = []
    upper = question.upper()
    for match in _TICKER.findall(upper):
        if match not in seen:
            seen.append(match)
    for name, ticker in _NAME_TO_TICKER.items():
        if re.search(r"\b" + name + r"\b", upper) and ticker not in seen:
            seen.append(ticker)
    return seen


def question_years(question: str) -> list[str]:
    """Fiscal or calendar years mentioned in the question text."""
    seen: list[str] = []
    for match in _YEAR.finditer(question or ""):
        year = match.group(1)
        if year not in seen:
            seen.append(year)
    return seen


def asks_exact_figure(question: str) -> bool:
    """True when the asker wants a precise count/volume, not qualitative MD&A."""
    return bool(_EXACT_FACT.search(question or ""))


def _overlap_count(question: str, text: str) -> int:
    q = set(_TOKEN.findall(question.lower()))
    t = set(_TOKEN.findall(text.lower()))
    stop = {"the", "a", "an", "of", "and", "or", "in", "to", "for", "what", "does", "do"}
    return len((q - stop) & t)


def evidence_has_year_near_quantity(
    chunks: list[RetrievedChunk],
    years: list[str],
    *,
    window: int = YEAR_QUANTITY_WINDOW,
    quantity_re: re.Pattern[str] | None = None,
) -> bool:
    """True when an asked year sits near a matching quantity in the same chunk.

    Filing_date is ignored. A year that only appears in a distant sentence
    (for example a 2012 store-opening note next to FY2024 revenue) does not
    count as period evidence for an exact-figure question.

    Pass ``quantity_re=UNIT_QUANTITY_RE`` so a year next to dollars does not
    satisfy a unit-volume ask when units only appear under another year.
    """
    if not years:
        return True
    pattern = quantity_re or _FACT_QUANTITY
    for chunk in chunks:
        text = chunk.text or ""
        for year in years:
            start = 0
            while True:
                idx = text.find(year, start)
                if idx < 0:
                    break
                lo = max(0, idx - window)
                hi = min(len(text), idx + len(year) + window)
                if pattern.search(text[lo:hi]):
                    return True
                start = idx + len(year)
    return False


def _evidence_mentions_year(chunks: list[RetrievedChunk], years: list[str]) -> bool:
    """Period must appear in chunk *text*, not merely in filing_date."""
    blob = " ".join(c.text for c in chunks)
    return any(year in blob for year in years)


def missing_cited_tickers(question: str, citations: list[Citation]) -> list[str]:
    """Named issuers that do not appear in the citation set."""
    wanted = mentioned_tickers(question)
    if len(wanted) < 2:
        return []
    cited = {c.ticker.upper() for c in citations if c.ticker}
    return [tkr for tkr in wanted if tkr not in cited]


def select_quote_indices(
    question: str,
    chunks: list[RetrievedChunk],
    *,
    limit: int = 3,
) -> list[int]:
    """Pick overlapping snippets, covering named tickers before rank order."""
    candidates = [
        i
        for i, chunk in enumerate(chunks, start=1)
        if _overlap_count(question, chunk.text) >= DEFAULT_MIN_OVERLAP
    ]
    if not candidates:
        return []
    wanted = mentioned_tickers(question)
    if len(wanted) < 2:
        return candidates[:limit]
    picked: list[int] = []
    covered: set[str] = set()
    for i in candidates:
        ticker = str(chunks[i - 1].payload.get("ticker", "")).upper()
        if ticker in wanted and ticker not in covered:
            picked.append(i)
            covered.add(ticker)
            if len(picked) >= limit:
                return picked
    for i in candidates:
        if i not in picked:
            picked.append(i)
            if len(picked) >= limit:
                break
    return picked


def should_refuse(
    chunks: list[RetrievedChunk],
    question: str,
    *,
    min_score: float = DEFAULT_MIN_SCORE,
    min_overlap: int = DEFAULT_MIN_OVERLAP,
) -> str | None:
    """Return a refusal reason, or None if generation may proceed."""
    if not chunks:
        return "no retrieved evidence"
    wanted = mentioned_tickers(question)
    if wanted:
        present = {str(c.payload.get("ticker", "")).upper() for c in chunks}
        missing = [tkr for tkr in wanted if tkr not in present]
        if missing:
            return "missing evidence for ticker(s) " + ", ".join(missing)
    best = max(c.score for c in chunks)
    if best < min_score:
        return f"top retrieval score {best:.4f} below {min_score:.4f}"
    if not any(_overlap_count(question, c.text) >= min_overlap for c in chunks):
        return "retrieved chunks do not overlap the question terms"
    if asks_exact_figure(question):
        years = question_years(question)
        if years and not _evidence_mentions_year(chunks, years):
            return "asked period " + ", ".join(years) + " not present in retrieved evidence"
        if years and not evidence_has_year_near_quantity(chunks, years):
            return (
                "asked period "
                + ", ".join(years)
                + " not near a quantity in retrieved evidence"
            )
        if asks_unit_volume(question):
            if years and not evidence_has_year_near_quantity(
                chunks, years, quantity_re=UNIT_QUANTITY_RE
            ):
                return (
                    "asked period "
                    + ", ".join(years)
                    + " not near a unit quantity in retrieved evidence"
                )
            if not evidence_has_unit_quantity(chunks):
                return "asked unit volume not present in retrieved evidence"
        segments = question_segments(question)
        if years and segments and not evidence_has_year_near_segment(
            chunks, years, segments, window=YEAR_QUANTITY_WINDOW
        ):
            return (
                "asked period "
                + ", ".join(years)
                + " not near segment "
                + ", ".join(segments)
                + " in retrieved evidence"
            )
    return None
