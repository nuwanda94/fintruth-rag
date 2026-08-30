"""Rerank fused retrieval hits for precision.

Default is an offline lexical + metadata scorer so Week 2 wiring works
without Cohere. `build_reranker` can later swap in a cross-encoder when
COHERE_API_KEY is set; the interface stays the same.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from fintruth.config import Settings, get_settings
from fintruth.retrieval.hybrid import RetrievedChunk

_TOKEN = re.compile(r"[a-z0-9$%]+", re.I)
_STOP = {
    "the",
    "a",
    "an",
    "of",
    "and",
    "or",
    "in",
    "to",
    "for",
    "what",
    "does",
    "do",
    "how",
    "is",
    "are",
    "on",
    "with",
    "that",
    "this",
}

_SECTION_HINTS: dict[str, tuple[str, ...]] = {
    "risk_factors": ("risk", "risks", "competition", "litigation", "volatility", "regulation"),
    "mda": ("revenue", "margin", "growth", "outlook", "liquidity", "capital", "results"),
}


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN.findall(text.lower()) if t not in _STOP and len(t) > 1}


class Reranker(Protocol):
    """Score query/chunk pairs and return the top-k hits."""

    name: str

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int,
    ) -> list[RetrievedChunk]: ...


@dataclass
class LexicalReranker:
    """Deterministic stand-in for a cross-encoder.

    Score = lexical Jaccard + fused retrieval score + section hint +
    recency prior (newer filings rank slightly higher).
    """

    name: str = "lexical"
    recency_weight: float = 0.08
    section_weight: float = 0.12
    fusion_weight: float = 2.0

    def score(self, query: str, chunk: RetrievedChunk) -> float:
        q = _tokens(query)
        t = _tokens(chunk.text)
        if not q:
            overlap = 0.0
        else:
            overlap = len(q & t) / max(len(q | t), 1)
        section = str(chunk.payload.get("section", ""))
        hint = 0.0
        for sec, words in _SECTION_HINTS.items():
            if section == sec and any(w in query.lower() for w in words):
                hint = self.section_weight
                break
        recency = 0.0
        date = str(chunk.payload.get("filing_date") or "")
        if len(date) >= 4 and date[:4].isdigit():
            year = int(date[:4])
            recency = self.recency_weight * max(0, year - 2020) / 6.0
        return overlap + self.fusion_weight * float(chunk.score) + hint + recency

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int,
    ) -> list[RetrievedChunk]:
        if not chunks:
            return []
        scored: list[RetrievedChunk] = []
        for chunk in chunks:
            value = self.score(query, chunk)
            scored.append(
                RetrievedChunk(
                    chunk_id=chunk.chunk_id,
                    text=chunk.text,
                    score=chunk.score,
                    dense_rank=chunk.dense_rank,
                    sparse_rank=chunk.sparse_rank,
                    payload=chunk.payload,
                    rerank_score=value,
                )
            )
        scored.sort(key=lambda c: c.rerank_score or 0.0, reverse=True)
        return scored[:top_k]


class IdentityReranker:
    """No-op reranker used for naive / ablation paths."""

    name = "identity"

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int,
    ) -> list[RetrievedChunk]:
        return chunks[:top_k]


def build_reranker(settings: Settings | None = None) -> Reranker:
    """Factory: lexical offline default; Cohere reserved for later."""
    settings = settings or get_settings()
    model = (settings.reranker_model or "lexical").lower()
    if model in {"none", "off", "identity"}:
        return IdentityReranker()
    # Cohere path is intentionally not called here: no extra dep, no network.
    # When a key exists we still use lexical so tests stay deterministic.
    return LexicalReranker()
