"""Evaluation dataset, metrics, ablation, and runner."""

from fintruth.eval.ablation import AblationSummary, run_retrieval_ablation
from fintruth.eval.dataset import EvalQuestion, load_questions
from fintruth.eval.metrics import (
    ItemScore,
    extract_numbers,
    resolve_cited_chunk,
    score_item,
    summarize,
)
from fintruth.eval.runner import run_eval

__all__ = [
    "AblationSummary",
    "EvalQuestion",
    "ItemScore",
    "extract_numbers",
    "load_questions",
    "resolve_cited_chunk",
    "run_eval",
    "run_retrieval_ablation",
    "score_item",
    "summarize",
]
