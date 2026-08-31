"""Citation parsing and answer footer helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from fintruth.generation.prompts import REFUSAL_PREFIX
from fintruth.generation.usage import TokenUsage
from fintruth.retrieval.hybrid import RetrievedChunk

_CITE = re.compile(r"\[(\d+)\]")


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
    usage: TokenUsage = field(default_factory=TokenUsage)

    def sources_block(self) -> str:
        """Render a Sources footer from parsed citations."""
        if not self.citations:
            return ""
        lines = ["Sources:"] + [c.format_line() for c in self.citations]
        return "\n".join(lines)


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


def format_citation_footer(citations: list[Citation]) -> str:
    """Stable Sources block used by extractive and LLM post-process paths."""
    if not citations:
        return ""
    return "Sources:\n" + "\n".join(c.format_line() for c in citations)


def attach_sources(answer: str, citations: list[Citation]) -> str:
    """Append a Sources footer if the body does not already include one."""
    if not citations or re.search(r"(?im)^sources:", answer):
        return answer
    return answer.rstrip() + "\n\n" + format_citation_footer(citations)


def parse_model_output(
    text: str, chunks: list[RetrievedChunk]
) -> tuple[bool, str, str | None, list[Citation]]:
    """Split a model reply into refusal vs cited answer."""
    stripped = text.strip()
    if stripped.upper().startswith(REFUSAL_PREFIX):
        reason = stripped[len(REFUSAL_PREFIX) :].strip() or "insufficient evidence"
        return True, stripped, reason, []
    cites = parse_citations(stripped, chunks)
    return False, stripped, None, cites
