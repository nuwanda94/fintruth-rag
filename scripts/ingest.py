"""CLI: download, parse, chunk, and catalog SEC filings.

Usage:
    uv run python scripts/ingest.py
    uv run python scripts/ingest.py --tickers AAPL MSFT --years 3
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running without installing the package.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fintruth.config import get_settings  # noqa: E402
from fintruth.ingestion.pipeline import run_ingest  # noqa: E402
from fintruth.logging import setup_logging  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest SEC 10-K / 10-Q filings.")
    parser.add_argument("--tickers", nargs="*", default=None, help="Override default ticker list")
    parser.add_argument("--years", type=int, default=None, help="Lookback years")
    args = parser.parse_args()

    setup_logging()
    settings = get_settings()
    if args.years is not None:
        settings.filing_years = args.years
    filings, chunks = run_ingest(tickers=args.tickers, settings=settings)
    print(f"ingest done: filings={filings} chunks={chunks}")
    return 0 if filings else 1


if __name__ == "__main__":
    raise SystemExit(main())
