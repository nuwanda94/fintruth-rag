"""CLI: run the seeded eval set through retrieve → generate → score."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fintruth.eval.dataset import load_questions  # noqa: E402
from fintruth.eval.runner import run_eval  # noqa: E402
from fintruth.logging import setup_logging  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run FinTruth offline eval harness.")
    parser.add_argument("--questions", type=Path, default=None, help="JSONL path")
    parser.add_argument("--demo", action="store_true", help="Force fixture corpus")
    parser.add_argument("--no-write", action="store_true", help="Do not persist results")
    args = parser.parse_args()

    setup_logging()
    questions = load_questions(args.questions) if args.questions else load_questions()
    run = run_eval(questions=questions, demo=args.demo, write=not args.no_write)
    print(f"# FinTruth eval  corpus={run.corpus}  n_chunks={run.n_chunks}  n={int(run.summary['n'])}")
    print(json.dumps(run.summary, indent=2))
    failed = [row for row in run.items if row["score"]["composite"] < 1.0]
    if failed:
        print(f"\nPartial / failed items ({len(failed)}):")
        for row in failed:
            s = row["score"]
            print(
                f"  {row['id']} refuse_ok={s['refusal_ok']} cite_ok={s['citation_ok']} "
                f"kw_ok={s['keyword_ok']} ticker_ok={s['ticker_ok']}  {row['question'][:72]}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
