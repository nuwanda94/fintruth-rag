"""Grounded generation: parse citations, refuse on weak evidence.

Default path is extractive (no LLM) so the retrieve → answer loop works
offline. When ``XAI_API_KEY`` is set, ``generate_answer`` may call Grok
and then re-apply the same citation / refusal gates.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from fintruth.config import Settings, get_settings
from fintruth.generation.prompts import REFUSAL_PREFIX, build_messages
from fintruth.generation.units import asks_unit_volume, evidence_has_unit_quantity
from fintruth.retrieval.hybrid import RetrievedChunk

_CITE = re.compile(r"\[(\d+)\]")
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

DEFAULT_MIN_SCORE = 0.012
DEFAULT_MIN_OVERLAP = 1

XAI_CHAT_URL = "https://api.x.ai/v1/chat/completions"


@dataclass(slots=True)
class Citation:
    """Pointer from an answer span back to a retrieved chunk."""

    index: int
    chunk_id: str
    ticker: str
    form: str
    section: str
    filing_date: str

    def format_line(self) -> str:
        """Interview-facing footnote line."""
        return (
            f"[{self.index}] {self.ticker} {self.form} {self.section} "
            f"{self.filing_date} ({self.chunk_id})"
        )


@dataclass(slots=True)
class GroundedAnswer:
    """Structured generation result handed to CLI / later UI."""

    question: str
    answer: str
    refused: bool
    refusal_reason: str | None
    citations: list[Citation] = field(default_factory=list)
    chunks: list[RetrievedChunk] = field(default_factory=list)
    mode: str = "extractive"

    def sources_block(self) -> str:
        """Render a Sources footer from parsed citations."""
        if not self.citations:
            return ""
        lines = ["Sources:"] + [c.format_line() for c in self.citations]
        return "\n".join(lines)
