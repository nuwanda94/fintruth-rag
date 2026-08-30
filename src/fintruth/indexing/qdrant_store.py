"""Vector store: Qdrant when available, otherwise an in-process fallback.

The in-memory store is enough for unit tests and local CLI without a
running Qdrant container. The payload schema matches what hybrid search
and later generation expect.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any

from fintruth.config import Settings, get_settings
from fintruth.indexing.embedder import Embedder, build_embedder

logger = logging.getLogger(__name__)


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=False))


@dataclass(slots=True)
class ScoredPoint:
    """A retrieved chunk plus similarity score."""

    chunk_id: str
    score: float
    payload: dict[str, Any]
    vector: list[float] | None = None


class VectorStore:
    """Common surface for upsert + dense kNN."""

    def ensure_collection(self, dim: int) -> None:
        raise NotImplementedError

    def upsert(self, ids: list[str], vectors: list[list[float]], payloads: list[dict]) -> int:
        raise NotImplementedError

    def search(
        self,
        query_vector: list[float],
        limit: int,
        where: dict[str, Any] | None = None,
    ) -> list[ScoredPoint]:
        raise NotImplementedError

    def count(self) -> int:
        raise NotImplementedError


class InMemoryVectorStore(VectorStore):
    """Process-local dense index used when Qdrant is not running."""

    def __init__(self, collection: str = "fintruth_chunks") -> None:
        self.collection = collection
        self.dim: int | None = None
        self._ids: list[str] = []
        self._vectors: list[list[float]] = []
        self._payloads: list[dict[str, Any]] = []
        self._by_id: dict[str, int] = {}

    def ensure_collection(self, dim: int) -> None:
        self.dim = dim

    def upsert(self, ids: list[str], vectors: list[list[float]], payloads: list[dict]) -> int:
        for cid, vec, payload in zip(ids, vectors, payloads, strict=True):
            if cid in self._by_id:
                i = self._by_id[cid]
                self._vectors[i] = vec
                self._payloads[i] = payload
            else:
                self._by_id[cid] = len(self._ids)
                self._ids.append(cid)
                self._vectors.append(vec)
                self._payloads.append(payload)
        return len(ids)

    def search(
        self,
        query_vector: list[float],
        limit: int,
        where: dict[str, Any] | None = None,
    ) -> list[ScoredPoint]:
        scored: list[ScoredPoint] = []
        for cid, vec, payload in zip(self._ids, self._vectors, self._payloads, strict=True):
            if where and not _payload_matches(payload, where):
                continue
            scored.append(
                ScoredPoint(
                    chunk_id=cid,
                    score=_cosine(query_vector, vec),
                    payload=payload,
                    vector=vec,
                )
            )
        scored.sort(key=lambda p: p.score, reverse=True)
        return scored[:limit]

    def count(self) -> int:
        return len(self._ids)


def _payload_matches(payload: dict[str, Any], where: dict[str, Any]) -> bool:
    for key, expected in where.items():
        value = payload.get(key)
        if isinstance(expected, (list, tuple, set)):
            if value not in expected:
                return False
        elif value != expected:
            return False
    return True


class QdrantVectorStore(VectorStore):
    """Thin wrapper around qdrant-client when the extra is installed."""

    def __init__(self, settings: Settings | None = None) -> None:
        from qdrant_client import QdrantClient
        from qdrant_client.http import models as qm

        self._qm = qm
        cfg = settings or get_settings()
        self.collection = cfg.qdrant_collection
        if cfg.qdrant_in_memory:
            self._client = QdrantClient(":memory:")
        else:
            self._client = QdrantClient(url=cfg.qdrant_url, api_key=cfg.qdrant_api_key or None)

    def ensure_collection(self, dim: int) -> None:
        from qdrant_client.http import models as qm

        existing = {c.name for c in self._client.get_collections().collections}
        if self.collection in existing:
            return
        self._client.create_collection(
            collection_name=self.collection,
            vectors_config=qm.VectorParams(size=dim, distance=qm.Distance.COSINE),
        )

    def upsert(self, ids: list[str], vectors: list[list[float]], payloads: list[dict]) -> int:
        from qdrant_client.http import models as qm

        points = [
            qm.PointStruct(id=_stable_point_id(cid), vector=vec, payload={**payload, "chunk_id": cid})
            for cid, vec, payload in zip(ids, vectors, payloads, strict=True)
        ]
        self._client.upsert(collection_name=self.collection, points=points)
        return len(points)

    def search(
        self,
        query_vector: list[float],
        limit: int,
        where: dict[str, Any] | None = None,
    ) -> list[ScoredPoint]:
        from qdrant_client.http import models as qm

        query_filter = _qdrant_filter(qm, where) if where else None
        hits = self._client.search(
            collection_name=self.collection,
            query_vector=query_vector,
            limit=limit,
            query_filter=query_filter,
            with_payload=True,
        )
        out: list[ScoredPoint] = []
        for hit in hits:
            payload = dict(hit.payload or {})
            out.append(
                ScoredPoint(
                    chunk_id=str(payload.get("chunk_id", hit.id)),
                    score=float(hit.score),
                    payload=payload,
                )
            )
        return out

    def count(self) -> int:
        return int(self._client.count(self.collection, exact=True).count)


def _stable_point_id(chunk_id: str) -> int:
    """Map string chunk ids onto a Qdrant-safe unsigned 64-bit int."""
    import hashlib

    digest = hashlib.blake2b(chunk_id.encode(), digest_size=8).digest()
    return int.from_bytes(digest, "big") % (2**63 - 1)


def _qdrant_filter(qm: Any, where: dict[str, Any]) -> Any:
    must = []
    for key, expected in where.items():
        if isinstance(expected, (list, tuple, set)):
            must.append(qm.FieldCondition(key=key, match=qm.MatchAny(any=list(expected))))
        else:
            must.append(qm.FieldCondition(key=key, match=qm.MatchValue(value=expected)))
    return qm.Filter(must=must)


def build_vector_store(settings: Settings | None = None) -> VectorStore:
    """Prefer Qdrant; fall back to in-memory if the client is missing."""
    cfg = settings or get_settings()
    try:
        return QdrantVectorStore(settings=cfg)
    except ImportError:
        logger.info("qdrant-client not installed; using InMemoryVectorStore")
        return InMemoryVectorStore(collection=cfg.qdrant_collection)


def index_payloads(
    payloads: list[dict[str, Any]],
    *,
    embedder: Embedder | None = None,
    store: VectorStore | None = None,
    settings: Settings | None = None,
    batch_size: int = 64,
) -> int:
    """Embed chunk payloads and upsert them into the vector store."""
    cfg = settings or get_settings()
    embedder = embedder or build_embedder(cfg)
    store = store or build_vector_store(cfg)
    store.ensure_collection(embedder.dim)
    total = 0
    for start in range(0, len(payloads), batch_size):
        batch = payloads[start : start + batch_size]
        texts = [str(p.get("text", "")) for p in batch]
        ids = [str(p.get("chunk_id", f"anon-{start + i}")) for i, p in enumerate(batch)]
        vectors = embedder.embed(texts)
        total += store.upsert(ids, vectors, batch)
    return total


def _unused_math() -> float:
    # keep math imported for future sparse-weight helpers without lint churn
    return math.nan
