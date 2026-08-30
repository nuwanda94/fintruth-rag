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
