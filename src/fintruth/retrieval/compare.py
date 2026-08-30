"""Naive vs hybrid vs hybrid+rerank comparison helper."""

from __future__ import annotations

from dataclasses import dataclass

from fintruth.retrieval.filters import RetrievalFilters
from fintruth.retrieval.hybrid import HybridRetriever, RetrievedChunk, RetrieveTrace


@dataclass(slots=True)
class AblationArm:
    """One retrieval configuration and its ranked ids."""

    name: str
    chunk_ids: list[str]
    traces: RetrieveTrace | None
    hits: list[RetrievedChunk]


def compare_retrievers(
    retriever: HybridRetriever,
    query: str,
    filters: RetrievalFilters | None = None,
    final_k: int = 5,
) -> list[AblationArm]:
    """Run dense-only, hybrid, and hybrid+rerank on the same query."""
    arms: list[AblationArm] = []
    specs: list[tuple[str, str, bool]] = [
        ("dense", "dense", False),
        ("hybrid", "hybrid", False),
        ("hybrid+rerank", "hybrid", True),
    ]
    for name, mode, rerank in specs:
        hits = retriever.retrieve(
            query,
            filters=filters,
            final_k=final_k,
            mode=mode,  # type: ignore[arg-type]
            rerank=rerank,
        )
        arms.append(
            AblationArm(
                name=name,
                chunk_ids=[h.chunk_id for h in hits],
                traces=retriever.last_trace,
                hits=hits,
            )
        )
    return arms
