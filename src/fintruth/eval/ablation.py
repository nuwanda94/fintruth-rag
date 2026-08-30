"""Offline retrieval ablation: dense vs hybrid vs hybrid+rerank."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from fintruth.eval.dataset import EvalQuestion
from fintruth.retrieval.compare import compare_retrievers
from fintruth.retrieval.filters import RetrievalFilters
from fintruth.retrieval.hybrid import HybridRetriever


@dataclass(slots=True)
class AblationSummary:
    """Keyword-in-top-k rates per retrieval arm."""

    n: int
    arms: dict[str, float]
    items: list[dict[str, Any]]


def _keyword_hit(question: EvalQuestion, chunk_texts: list[str]) -> bool:
    if question.expect_refuse or not question.keywords:
        return True
    blob = " ".join(chunk_texts).lower()
    return any(k in blob for k in question.keywords)


def run_retrieval_ablation(
    questions: list[EvalQuestion],
    retriever: HybridRetriever,
    *,
    final_k: int = 5,
) -> AblationSummary:
    """Score whether gold keywords appear in each arm's retrieved texts."""
    tallies: dict[str, list[bool]] = {}
    items: list[dict[str, Any]] = []
    for question in questions:
        filters = RetrievalFilters(
            tickers=question.tickers,
            forms=question.forms,
            sections=question.sections,
        )
        arms = compare_retrievers(
            retriever, question.question, filters=filters, final_k=final_k
        )
        row: dict[str, Any] = {"id": question.id, "arms": {}}
        for arm in arms:
            texts = [h.text for h in arm.hits]
            hit = _keyword_hit(question, texts)
            tallies.setdefault(arm.name, []).append(hit)
            row["arms"][arm.name] = {
                "keyword_hit": hit,
                "chunk_ids": arm.chunk_ids,
            }
        items.append(row)

    rates = {
        name: (sum(flags) / len(flags) if flags else 0.0)
        for name, flags in tallies.items()
    }
    return AblationSummary(n=len(questions), arms=rates, items=items)


def ablation_as_dict(summary: AblationSummary) -> dict[str, Any]:
    """JSON-ready payload stored next to eval run results."""
    return asdict(summary)
