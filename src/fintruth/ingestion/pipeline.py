"""End-to-end ingest: download → parse → chunk → catalog."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fintruth.config import Settings, get_settings
from fintruth.ingestion.catalog import Catalog
from fintruth.ingestion.chunker import Chunk, chunk_section
from fintruth.ingestion.downloader import FilingRef, download_filings
from fintruth.ingestion.parser import parse_filing_html

logger = logging.getLogger(__name__)


def run_ingest(
    tickers: list[str] | None = None,
    settings: Settings | None = None,
) -> tuple[int, int]:
    """Download filings, write processed JSONL chunks, and upsert the SQLite catalog.

    Returns (filings_processed, chunks_written).
    """
    cfg = settings or get_settings()
    processed_dir = Path(cfg.data_processed_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)

    refs = download_filings(tickers=tickers, settings=cfg)
    catalog = Catalog(settings=cfg)
    all_chunks: list[Chunk] = []
    filings_ok = 0

    for ref in refs:
        if not ref.local_path or not Path(ref.local_path).exists():
            continue
        try:
            sections = parse_filing_html(ref.local_path)
            chunks: list[Chunk] = []
            for section in sections:
                chunks.extend(chunk_section(section, ref, settings=cfg))
            catalog.upsert_filing(ref)
            catalog.upsert_chunks(chunks)
            out = processed_dir / f"{ref.ticker}_{ref.form}_{ref.accession}.jsonl"
            with out.open("w", encoding="utf-8") as fh:
                for chunk in chunks:
                    fh.write(json.dumps(chunk.payload(), ensure_ascii=False) + "\n")
            all_chunks.extend(chunks)
            filings_ok += 1
            logger.info(
                "Processed %s %s %s — %s sections, %s chunks",
                ref.ticker,
                ref.form,
                ref.accession,
                len(sections),
                len(chunks),
            )
        except Exception:
            logger.exception("Failed processing %s %s", ref.ticker, ref.accession)

    catalog.close()
    logger.info("Ingest complete: %s filings, %s chunks", filings_ok, len(all_chunks))
    return filings_ok, len(all_chunks)
