"""Evaluation dataset, metrics, and runner (Week 1 Day 5+)."""

from fintruth.eval.dataset import EvalQuestion, load_questions
from fintruth.eval.metrics import ItemScore, score_item, summarize
from fintruth.eval.runner import run_eval

__all__ = [
    "EvalQuestion",
    "ItemScore",
    "load_questions",
    "run_eval",
    "score_item",
    "summarize",
]
