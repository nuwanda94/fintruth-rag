"""Download 10-K / 10-Q filings via edgartools."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from fintruth.config import Settings, get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class FilingRef:
    """Pointer to a single SEC filing on disk (or to be fetched)."""

    ticker: str
    cik: str
    form: str
    filing_date: str
    accession: str
    local_path: Path | None = None
    source_url: str | None = None


def _ensure_identity(user_agent: str) -> None:
    """SEC requires a descriptive User-Agent; edgartools reads identity from env/set_identity."""
    try:
        from edgar import set_identity

        set_identity(user_agent)
    except Exception as exc:  # pragma: no cover - optional until edgartools is installed
        logger.warning("Could not set edgartools identity: %s", exc)


def download_filings(
    tickers: list[str] | None = None,
    forms: list[str] | None = None,
    years: int | None = None,
    settings: Settings | None = None,
    max_filings: int | None = None,
) -> list[FilingRef]:
    """Fetch recent 10-K/10-Q HTML for each ticker and write under data/raw.

    Returns lightweight refs even if a ticker fails so the pipeline can continue.
    ``max_filings`` caps *successful* writes per ticker for a smoke ingest.
    """
    cfg = settings or get_settings()
    tickers = tickers or cfg.tickers
    forms = forms or cfg.filing_forms
    years = years if years is not None else cfg.filing_years
    raw_root = Path(cfg.data_raw_dir)
    raw_root.mkdir(parents=True, exist_ok=True)
    _ensure_identity(cfg.sec_user_agent)

    cutoff_year = date.today().year - years + 1
    refs: list[FilingRef] = []

    try:
        from edgar import Company
    except ImportError:
        logger.error("edgartools is not installed. Run `uv sync` then retry.")
        return refs

    for ticker in tickers:
        try:
            company = Company(ticker)
            cik = str(company.cik)
            filings = company.get_filings(form=forms)
            count = 0
            for filing in filings:
                if max_filings is not None and count >= max_filings:
                    break
                filing_date = str(getattr(filing, "filing_date", "") or "")
                year = int(filing_date[:4]) if filing_date[:4].isdigit() else 0
                if year and year < cutoff_year:
                    break
                form = str(getattr(filing, "form", "") or "")
                accession = str(
                    getattr(filing, "accession_number", None)
                    or getattr(filing, "accession_no", "")
                    or "unknown"
                ).replace(":", "-")
                dest_dir = raw_root / ticker / form / accession
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest = dest_dir / "filing.html"
                if not dest.exists():
                    html = filing.html()
                    if not html:
                        logger.warning("Empty HTML for %s %s %s", ticker, form, accession)
                        continue
                    dest.write_text(
                        html if isinstance(html, str) else html.decode("utf-8", "replace"),
                        encoding="utf-8",
                    )
                refs.append(
                    FilingRef(
                        ticker=ticker,
                        cik=cik,
                        form=form,
                        filing_date=filing_date,
                        accession=accession,
                        local_path=dest,
                        source_url=str(getattr(filing, "homepage_url", "") or ""),
                    )
                )
                count += 1
            logger.info("Downloaded/cached %s filings for %s", count, ticker)
        except Exception as exc:
            logger.exception("Failed downloading filings for %s: %s", ticker, exc)

    return refs
