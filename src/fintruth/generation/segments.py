"""Lexical geography / reporting-segment helpers for exact-figure gates."""

from __future__ import annotations

import re

from fintruth.retrieval.hybrid import RetrievedChunk

# Longest aliases first so "greater china" wins over a bare "china" scan.
_SEGMENT_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("greater china", ("greater china",)),
    ("rest of asia pacific", ("rest of asia pacific", "asia-pacific", "asia pacific")),
    ("americas", ("americas",)),
    ("europe", ("europe",)),
    ("japan", ("japan",)),
)


def question_segments(question: str) -> list[str]:
    """Canonical reporting segments named in the question, if any."""
    text = (question or "").lower()
    found: list[str] = []
    for canonical, aliases in _SEGMENT_ALIASES:
        if any(alias in text for alias in aliases) and canonical not in found:
            found.append(canonical)
    return found


def evidence_has_year_near_segment(
    chunks: list[RetrievedChunk],
    years: list[str],
    segments: list[str],
    *,
    window: int,
) -> bool:
    """True when an asked year sits near a named reporting segment.

    Used after the year-quantity window so Americas units in FY2012 cannot
    answer a Greater China unit-volume question. Still character distance,
    not XBRL line-item roles.
    """
    if not years or not segments:
        return True
    patterns = [re.compile(re.escape(seg), re.I) for seg in segments]
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
                span = text[lo:hi]
                if all(pat.search(span) for pat in patterns):
                    return True
                start = idx + len(year)
    return False
