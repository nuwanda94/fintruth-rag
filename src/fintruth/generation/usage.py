"""Token and latency accounting for grounded generation.

Extractive answers have no API bill. We still estimate tokens so the
interview demo can show context size. When Grok returns ``usage``,
prefer those numbers over the character heuristic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from fintruth.retrieval.hybrid import RetrievedChunk

CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """Cheap char/4 estimate. Empty text is 0 tokens."""
    if not text:
        return 0
    return max(1, (len(text) + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN)


@dataclass(slots=True)
class TokenUsage:
    """Prompt + completion tokens for one generate or refuse call."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    source: str = "estimate"

    def __post_init__(self) -> None:
        if self.total_tokens <= 0:
            self.total_tokens = self.prompt_tokens + self.completion_tokens

    def as_dict(self) -> dict[str, Any]:
        """JSON-friendly snapshot for eval rows and CLI."""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "source": self.source,
        }


def usage_from_api(payload: Mapping[str, Any] | None) -> TokenUsage | None:
    """Parse OpenAI-style ``usage`` from an xAI chat completion body."""
    if not payload:
        return None
    raw = payload.get("usage")
    if not isinstance(raw, Mapping):
        return None
    prompt = int(raw.get("prompt_tokens") or 0)
    completion = int(raw.get("completion_tokens") or 0)
    total = int(raw.get("total_tokens") or 0)
    if prompt <= 0 and completion <= 0 and total <= 0:
        return None
    return TokenUsage(
        prompt_tokens=prompt,
        completion_tokens=completion,
        total_tokens=total or (prompt + completion),
        source="api",
    )


def measure_usage(
    question: str,
    chunks: list[RetrievedChunk],
    answer: str,
    *,
    api_usage: TokenUsage | None = None,
) -> TokenUsage:
    """Prefer API usage; otherwise estimate from question + evidence + answer."""
    if api_usage is not None:
        return api_usage
    prompt = question + "\n" + "\n".join(chunk.text for chunk in chunks)
    prompt_tokens = estimate_tokens(prompt)
    completion_tokens = estimate_tokens(answer)
    return TokenUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        source="estimate",
    )
