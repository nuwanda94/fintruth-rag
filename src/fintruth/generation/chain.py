"""Grounded generation: parse citations, refuse on weak evidence.

Default path is extractive (no LLM) so the retrieve → answer loop works
offline. When XAI_API_KEY is set, `llm_complete` can be swapped in later.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from fintruth.generation.prompts import REFUSAL_PREFIX, build_messages
from fintruth.retrieval.hybrid import RetrievedChunk

_CITE = re.compile(r"\[(\d+)\]")
_TOKEN = re.compile(r"[a-z0-9$%]+", re.I)

# RRF scores are typically ~0.03–0.04 for a single list hit; require at least
# one fused document above this floor before answering.
DEFAULT_MIN_SCORE = 0.012
DEFAULT_MIN_OVERLAP = 1


@dataclass(slots=True)
class Citation:
    """Pointer from an answer span back to a retrieved chunk."""

    index: int
    chunk_id: str
    ticker: str
    form: str
    section: str
    filing_date: str


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


def parse_citations(text: str, chunks: list[RetrievedChunk]) -> list[Citation]:
    """Extract [n] markers and map them onto retrieved chunks (1-indexed)."""
    seen: set[int] = set()
    out: list[Citation] = []
    for raw in _CITE.findall(text):
        idx = int(raw)
        if idx in seen or idx < 1 or idx > len(chunks):
            continue
        seen.add(idx)
        chunk = chunks[idx - 1]
        out.append(
            Citation(
                index=idx,
                chunk_id=chunk.chunk_id,
                ticker=str(chunk.payload.get("ticker", "")),
                form=str(chunk.payload.get("form", "")),
                section=str(chunk.payload.get("section", "")),
                filing_date=str(chunk.payload.get("filing_date", "")),
            )
        )
    return out


def parse_model_output(text: str, chunks: list[RetrievedChunk]) -> tuple[bool, str, str | None, list[Citation]]:
    """Split a model reply into refusal vs cited answer."""
    stripped = text.strip()
    if stripped.upper().startswith(REFUSAL_PREFIX):
        reason = stripped[len(REFUSAL_PREFIX) :].strip() or "insufficient evidence"
        return True, stripped, reason, []
    return False, stripped, None, parse_citations(stripped, chunks)


def _overlap_count(question: str, text: str) -> int:
    q = set(_TOKEN.findall(question.lower()))
    t = set(_TOKEN.findall(text.lower()))
    stop = {"the", "a", "an", "of", "and", "or", "in", "to", "for", "what", "does", "do"}
    return len((q - stop) & t)


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
    best = max(c.score for c in chunks)
    if best < min_score:
        return f"top retrieval score {best:.4f} below {min_score:.4f}"
    if not any(_overlap_count(question, c.text) >= min_overlap for c in chunks):
        return "retrieved chunks do not overlap the question terms"
    return None


def extractive_answer(question: str, chunks: list[RetrievedChunk]) -> GroundedAnswer:
    """Offline grounded path: quote supporting snippets with [n] citations."""
    reason = should_refuse(chunks, question)
    if reason:
        text = f"{REFUSAL_PREFIX} {reason}"
        return GroundedAnswer(
            question=question,
            answer=text,
            refused=True,
            refusal_reason=reason,
            citations=[],
            chunks=chunks,
            mode="extractive",
        )

    lines: list[str] = []
    used: list[int] = []
    for i, chunk in enumerate(chunks, start=1):
        if _overlap_count(question, chunk.text) < DEFAULT_MIN_OVERLAP:
            continue
        snippet = chunk.text.strip()
        if len(snippet) > 320:
            snippet = snippet[:317] + "..."
        lines.append(f"{snippet} [{i}]")
        used.append(i)
        if len(used) >= 3:
            break
    if not lines:
        reason = "no overlapping evidence after filtering"
        text = f"{REFUSAL_PREFIX} {reason}"
        return GroundedAnswer(
            question=question,
            answer=text,
            refused=True,
            refusal_reason=reason,
            citations=[],
            chunks=chunks,
            mode="extractive",
        )
    answer = "Based on the retrieved SEC excerpts:\n" + "\n".join(f"- {line}" for line in lines)
    return GroundedAnswer(
        question=question,
        answer=answer,
        refused=False,
        refusal_reason=None,
        citations=parse_citations(answer, chunks),
        chunks=chunks,
        mode="extractive",
    )


def generate_answer(
    question: str,
    chunks: list[RetrievedChunk],
    *,
    model_text: str | None = None,
) -> GroundedAnswer:
    """Build a GroundedAnswer from retrieve hits.

    Pass `model_text` when an LLM already produced a completion; otherwise
    fall back to the extractive offline path.
    """
    if model_text is None:
        return extractive_answer(question, chunks)
    refused, answer, reason, cites = parse_model_output(model_text, chunks)
    return GroundedAnswer(
        question=question,
        answer=answer,
        refused=refused,
        refusal_reason=reason,
        citations=cites,
        chunks=chunks,
        mode="llm",
    )


def prompt_for(question: str, chunks: list[RetrievedChunk]) -> list[dict[str, str]]:
    """Public helper so callers can inspect the grounded prompt."""
    return build_messages(question, chunks)
