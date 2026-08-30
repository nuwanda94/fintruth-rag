"""Load the interview eval set from evals/questions.jsonl."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from fintruth.config import REPO_ROOT

DEFAULT_EVAL_PATH = REPO_ROOT / "evals" / "questions.jsonl"


def _keywords_by_ticker(raw: dict) -> dict[str, list[str]]:
    mapping = raw.get("keywords_by_ticker") or {}
    out: dict[str, list[str]] = {}
    if not isinstance(mapping, dict):
        return out
    for ticker, needles in mapping.items():
        key = str(ticker).upper().strip()
        if not key:
            continue
        out[key] = [str(k).lower() for k in (needles or [])]
    return out


@dataclass(slots=True)
class EvalQuestion:
    """One grounded-research item used by the eval runner."""

    id: str
    question: str
    tickers: list[str] = field(default_factory=list)
    forms: list[str] = field(default_factory=list)
    sections: list[str] = field(default_factory=list)
    expect_refuse: bool = False
    must_cite: bool = True
    keywords: list[str] = field(default_factory=list)
    keywords_by_ticker: dict[str, list[str]] = field(default_factory=dict)
    difficulty: str = "medium"
    category: str = "general"
    expected_numbers: list[str] = field(default_factory=list)

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
            keywords_by_ticker=_keywords_by_ticker(raw),
            difficulty=str(raw.get("difficulty", "medium")),
            category=str(raw.get("category", "general")),
            expected_numbers=[str(n) for n in (raw.get("expected_numbers") or [])],
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
