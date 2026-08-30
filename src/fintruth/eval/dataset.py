"""Load the interview eval set from evals/questions.jsonl."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from fintruth.config import REPO_ROOT

DEFAULT_EVAL_PATH = REPO_ROOT / "evals" / "questions.jsonl"


@dataclass(slots=True)
class EvalQuestion:
    """One grounded-research item used by the Week 1 runner."""

    id: str
    question: str
    tickers: list[str] = field(default_factory=list)
    forms: list[str] = field(default_factory=list)
    sections: list[str] = field(default_factory=list)
    expect_refuse: bool = False
    must_cite: bool = True
    keywords: list[str] = field(default_factory=list)
    difficulty: str = "medium"
    category: str = "general"

    @classmethod
    def from_dict(cls, raw: dict) -> "EvalQuestion":
        return cls(
            id=str(raw["id"]),
            question=str(raw["question"]),
            tickers=list(raw.get("tickers") or []),
            forms=list(raw.get("forms") or []),
            sections=list(raw.get("sections") or []),
            expect_refuse=bool(raw.get("expect_refuse", False)),
            must_cite=bool(raw.get("must_cite", True)),
            keywords=[str(k).lower() for k in (raw.get("keywords") or [])],
            difficulty=str(raw.get("difficulty", "medium")),
            category=str(raw.get("category", "general")),
        )


def load_questions(path: Path | None = None) -> list[EvalQuestion]:
    """Parse JSONL; skip blank lines."""
    target = path or DEFAULT_EVAL_PATH
    items: list[EvalQuestion] = []
    text = target.read_text(encoding="utf-8")
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            raw = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at {target}:{line_no}") from exc
        items.append(EvalQuestion.from_dict(raw))
    return items
