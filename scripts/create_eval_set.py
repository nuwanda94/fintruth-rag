"""CLI: report or rewrite the seeded evals/questions.jsonl file."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fintruth.eval.dataset import DEFAULT_EVAL_PATH, load_questions  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect the seeded eval JSONL.")
    parser.add_argument("--path", type=Path, default=DEFAULT_EVAL_PATH)
    args = parser.parse_args()
    items = load_questions(args.path)
    refuse = sum(1 for q in items if q.expect_refuse)
    print(f"{args.path}  n={len(items)}  expect_refuse={refuse}  answer={len(items) - refuse}")
    for q in items:
        flag = "REFUSE" if q.expect_refuse else q.difficulty
        print(f"  {q.id} [{flag}/{q.category}] {q.question}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
