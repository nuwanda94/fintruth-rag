"""Hybrid dense + sparse retrieval with Reciprocal Rank Fusion."""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from fintruth.config import Settings, get_settings
from fintruth.indexing.embedder import Embedder, build_embedder
from fintruth.indexing.qdrant_store import ScoredPoint, VectorStore
from fintruth.retrieval.filters import RetrievalFilters

_TOKEN = re.compile(r"[a-z0-9$%]+", re.I)


@dataclass(slots=True)
class RetrievedChunk:
    """Ranked evidence unit handed to generation."""

    chunk_id: str
    text: str
    score: float
    dense_rank: int | None
    sparse_rank: int | None
    payload: dict[str, Any]


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class SparseIndex:
    """Tiny in-process BM25-ish index over chunk payloads."""

    def __init__(self, k1: float = 1.2, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._docs: list[tuple[str, dict[str, Any], list[str]]] = []
        self._df: Counter[str] = Counter()
        self._avgdl = 0.0

    def add(self, chunk_id: str, payload: dict[str, Any]) -> None:
        tokens = tokenize(str(payload.get("text", "")))
        self._docs.append((chunk_id, payload, tokens))
        self._df.update(set(tokens))
        n = len(self._docs)
        self._avgdl = ((self._avgdl * (n - 1)) + len(tokens)) / n

    def search(
        self,
        query: str,
        limit: int,
        filters: RetrievalFilters | None = None,
    ) -> list[ScoredPoint]:
        q_tokens = tokenize(query)
        if not q_tokens or not self._docs:
            return []
        n_docs = len(self._docs)
        scored: list[ScoredPoint] = []
        for chunk_id, payload, tokens in self._docs:
            if filters and not filters.allows(payload):
                continue
            tf = Counter(tokens)
            dl = len(tokens) or 1
            score = 0.0
            for term in q_tokens:
                if term not in tf:
                    continue
                df = self._df[term]
                idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
                denom = tf[term] + self.k1 * (1 - self.b + self.b * dl / (self._avgdl or 1.0))
                score += idf * (tf[term] * (self.k1 + 1) / denom)
            if score > 0:
                scored.append(ScoredPoint(chunk_id=chunk_id, score=score, payload=payload))
        scored.sort(key=lambda p: p.score, reverse=True)
        return scored[:limit]


def reciprocal_rank_fusion(
    ranked_lists: list[list[ScoredPoint]],
    k: int = 60,
) -> list[tuple[str, float, dict[str, Any]]]:
    """RRF: score = sum 1 / (k + rank) across retrievers."""
    scores: dict[str, float] = defaultdict(float)
    payload_by_id: dict[str, dict[str, Any]] = {}
    for results in ranked_lists:
        for rank, point in enumerate(results, start=1):
            scores[point.chunk_id] += 1.0 / (k + rank)
            payload_by_id[point.chunk_id] = point.payload
    fused = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return [(cid, score, payload_by_id[cid]) for cid, score in fused]


class HybridRetriever:
    """Dense kNN + sparse BM25 fused with RRF, then metadata-filtered."""

    def __init__(
        self,
        store: VectorStore,
        embedder: Embedder | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.store = store
        self.settings = settings or get_settings()
        self.embedder = embedder or build_embedder(self.settings)
        self.sparse = SparseIndex()

    def add_sparse_corpus(self, payloads: list[dict[str, Any]]) -> None:
        for payload in payloads:
            chunk_id = str(payload.get("chunk_id", ""))
            if chunk_id:
                self.sparse.add(chunk_id, payload)

    def retrieve(
        self,
        query: str,
        filters: RetrievalFilters | None = None,
        final_k: int | None = None,
    ) -> list[RetrievedChunk]:
        cfg = self.settings
        filters = filters or RetrievalFilters()
        qvec = self.embedder.embed_query(query)
        dense = self.store.search(
            qvec,
            limit=cfg.retrieve_dense_k,
            where=filters.to_where() or None,
        )
        dense = [p for p in dense if filters.allows(p.payload)]
        sparse = self.sparse.search(query, limit=cfg.retrieve_sparse_k, filters=filters)

        dense_rank = {p.chunk_id: i + 1 for i, p in enumerate(dense)}
        sparse_rank = {p.chunk_id: i + 1 for i, p in enumerate(sparse)}
        fused = reciprocal_rank_fusion([dense, sparse])
        limit = final_k or cfg.retrieve_final_k
        out: list[RetrievedChunk] = []
        for chunk_id, score, payload in fused[:limit]:
            out.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    text=str(payload.get("text", "")),
                    score=score,
                    dense_rank=dense_rank.get(chunk_id),
                    sparse_rank=sparse_rank.get(chunk_id),
                    payload=payload,
                )
            )
        return out
