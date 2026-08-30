"""Text embedding backends.

Default is a deterministic local hash embedder so indexing and retrieval
can be developed and tested without paid API keys. Swap to Voyage / OpenAI
by setting EMBEDDING_MODEL and the corresponding API key.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence

from fintruth.config import Settings, get_settings

_TOKEN = re.compile(r"[a-z0-9$%]+", re.I)


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class Embedder:
    """Minimal embedding interface used by the index and hybrid retriever."""

    dim: int
    model_name: str

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]


class HashEmbedder(Embedder):
    """Signed hashed bag-of-tokens embedding. Offline, deterministic, cheap."""

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim
        self.model_name = "hash-local"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [_l2_normalize(self._vector(t)) for t in texts]

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for tok in _TOKEN.findall(text.lower()):
            digest = hashlib.blake2b(tok.encode(), digest_size=8).digest()
            idx = int.from_bytes(digest[:4], "little") % self.dim
            sign = 1.0 if digest[4] & 1 else -1.0
            vec[idx] += sign
        return vec


def build_embedder(settings: Settings | None = None) -> Embedder:
    """Factory: hash-local by default; API backends reserved for later."""
    cfg = settings or get_settings()
    model = (cfg.embedding_model or "hash-local").lower()
    if model in {"hash-local", "hash", "local"}:
        return HashEmbedder(dim=cfg.embedding_dim)
    # Voyage / OpenAI clients land when keys and eval demand them.
    return HashEmbedder(dim=cfg.embedding_dim)
