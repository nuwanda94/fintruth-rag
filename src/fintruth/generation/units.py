"""Unit-volume helpers shared by generation gates and eval scoring."""

from __future__ import annotations

import re

from fintruth.retrieval.hybrid import RetrievedChunk

_UNIT_ASK = re.compile(
    r"\b(unit volume|units?|deliveries|shipments)\b",
    re.I,
)
# Number paired with units/deliveries/shipments. Dollar figures do not match.
UNIT_QUANTITY_RE = re.compile(
    r"\d[\d,]*(?:\.\d+)?\s*(?:thousand|million|billion)?\s*"
    r"(?:units?|deliveries|shipments)\b"
    r"|\b(?:units?|deliveries|shipments)\b.{0,40}\d",
    re.I,
)


def asks_unit_volume(question: str) -> bool:
    """True when the asker wants unit counts, not dollar revenue."""
    return bool(_UNIT_ASK.search(question or ""))


def evidence_has_unit_quantity(chunks: list[RetrievedChunk]) -> bool:
    """True when some chunk pairs a number with units/deliveries/shipments."""
    blob = " ".join(c.text for c in chunks)
    return bool(UNIT_QUANTITY_RE.search(blob))
