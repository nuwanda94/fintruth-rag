"""CLI: download, parse, chunk, and catalog SEC filings.

Usage:
    uv run python scripts/ingest.py --preflight
    uv run python scripts/ingest.py --tickers AAPL --years 1 --max-filings 1
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
from fintruth.ingestion.preflight import run_preflight  # noqa: E402
from fintruth.logging import setup_logging  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest SEC 10-K / 10-Q filings.")
    parser.add_argument("--tickers", nargs="*", default=None, help="Override default ticker list")
    parser.add_argument("--years", type=int, default=None, help="Lookback years")
    parser.add_argument(
        "--max-filings",
        type=int,
        default=None,
        help="Cap successful downloads per ticker (smoke ingest)",
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Check SEC_USER_AGENT / edgartools / data dirs; do not download",
    )
    parser.add_argument(
        "--check-network",
        action="store_true",
        help="With --preflight, GET data.sec.gov (needs a real User-Agent)",
    )
    args = parser.parse_args()

    setup_logging()
    settings = get_settings()
    if args.years is not None:
        settings.filing_years = args.years

    if args.preflight:
        result = run_preflight(settings, check_network=args.check_network)
        print("\n".join(result.lines()))
        return 0 if result.ready else 2

    gate = run_preflight(settings, check_network=False)
    if not gate.ready:
        print("\n".join(gate.lines()))
        print("Refusing live ingest. Set SEC_USER_AGENT in .env or run --preflight.")
        return 2

    filings, chunks = run_ingest(
        tickers=args.tickers,
        settings=settings,
        max_filings=args.max_filings,
    )
    print(f"ingest done: filings={filings} chunks={chunks}")
    return 0 if filings else 1


if __name__ == "__main__":
    raise SystemExit(main())
