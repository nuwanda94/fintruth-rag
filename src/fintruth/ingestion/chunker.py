"""Token-aware chunking of parsed sections."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fintruth.config import Settings, get_settings
from fintruth.ingestion.downloader import FilingRef
from fintruth.ingestion.parser import ParsedSection


@dataclass(slots=True)
class Chunk:
    """A retrieval unit with rich payload metadata."""

    chunk_id: str
    text: str
    ticker: str
    cik: str
    form: str
    filing_date: str
    accession: str
    section: str
    section_title: str
    chunk_index: int
    token_count: int
    extra: dict[str, Any] = field(default_factory=dict)

    def payload(self) -> dict[str, Any]:
        """Qdrant-ready metadata (no embedding)."""
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "ticker": self.ticker,
            "cik": self.cik,
            "form": self.form,
            "filing_date": self.filing_date,
            "accession": self.accession,
            "section": self.section,
            "section_title": self.section_title,
            "chunk_index": self.chunk_index,
            "token_count": self.token_count,
            **self.extra,
        }


def _count_tokens(text: str) -> int:
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return max(1, len(text.split()))


def _split_by_tokens(text: str, size: int, overlap: int) -> list[str]:
    paragraphs = [p.strip() for p in re_split_paragraphs(text) if p.strip()]
    chunks: list[str] = []
    buf: list[str] = []
    buf_tokens = 0
    for para in paragraphs:
        n = _count_tokens(para)
        if buf and buf_tokens + n > size:
            chunks.append("\n\n".join(buf))
            if overlap > 0 and buf:
                keep: list[str] = []
                keep_tokens = 0
                for piece in reversed(buf):
                    pt = _count_tokens(piece)
                    if keep_tokens + pt > overlap:
                        break
                    keep.append(piece)
                    keep_tokens += pt
                buf = list(reversed(keep))
                buf_tokens = keep_tokens
            else:
                buf, buf_tokens = [], 0
        buf.append(para)
        buf_tokens += n
    if buf:
        chunks.append("\n\n".join(buf))
    return chunks or ([text.strip()] if text.strip() else [])


def re_split_paragraphs(text: str) -> list[str]:
    parts = text.replace("\r\n", "\n").split("\n")
    merged: list[str] = []
    buf: list[str] = []
    for line in parts:
        if not line.strip():
            if buf:
                merged.append(" ".join(buf))
                buf = []
            continue
        buf.append(line.strip())
    if buf:
        merged.append(" ".join(buf))
    return merged


def chunk_section(
    section: ParsedSection,
    filing: FilingRef,
    settings: Settings | None = None,
) -> list[Chunk]:
    """Split one section into overlapping token windows with filing metadata."""
    cfg = settings or get_settings()
    pieces = _split_by_tokens(section.text, cfg.chunk_tokens, cfg.chunk_overlap_tokens)
    out: list[Chunk] = []
    for i, piece in enumerate(pieces):
        chunk_id = f"{filing.ticker}:{filing.accession}:{section.name}:{i}"
        out.append(
            Chunk(
                chunk_id=chunk_id,
                text=piece,
                ticker=filing.ticker,
                cik=filing.cik,
                form=filing.form,
                filing_date=filing.filing_date,
                accession=filing.accession,
                section=section.name,
                section_title=section.title,
                chunk_index=i,
                token_count=_count_tokens(piece),
            )
        )
    return out
