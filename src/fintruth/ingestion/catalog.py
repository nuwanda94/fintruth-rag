"""SQLite catalog of filings and chunks."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from fintruth.config import Settings, get_settings
from fintruth.ingestion.chunker import Chunk
from fintruth.ingestion.downloader import FilingRef

SCHEMA = """
CREATE TABLE IF NOT EXISTS filings (
    accession TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    cik TEXT NOT NULL,
    form TEXT NOT NULL,
    filing_date TEXT NOT NULL,
    local_path TEXT,
    source_url TEXT
);
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    accession TEXT NOT NULL,
    ticker TEXT NOT NULL,
    form TEXT NOT NULL,
    filing_date TEXT NOT NULL,
    section TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    token_count INTEGER NOT NULL,
    text TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    FOREIGN KEY (accession) REFERENCES filings(accession)
);
CREATE INDEX IF NOT EXISTS idx_chunks_ticker ON chunks(ticker);
CREATE INDEX IF NOT EXISTS idx_chunks_section ON chunks(section);
CREATE INDEX IF NOT EXISTS idx_filings_ticker_form ON filings(ticker, form);
"""


class Catalog:
    """Thin SQLite wrapper used during ingest and later eval."""

    def __init__(self, path: Path | None = None, settings: Settings | None = None) -> None:
        cfg = settings or get_settings()
        self.path = Path(path or cfg.catalog_db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def upsert_filing(self, filing: FilingRef) -> None:
        self._conn.execute(
            """
            INSERT INTO filings (accession, ticker, cik, form, filing_date, local_path, source_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(accession) DO UPDATE SET
                ticker=excluded.ticker,
                local_path=excluded.local_path,
                source_url=excluded.source_url
            """,
            (
                filing.accession,
                filing.ticker,
                filing.cik,
                filing.form,
                filing.filing_date,
                str(filing.local_path) if filing.local_path else None,
                filing.source_url,
            ),
        )
        self._conn.commit()

    def upsert_chunks(self, chunks: list[Chunk]) -> None:
        rows = [
            (
                c.chunk_id,
                c.accession,
                c.ticker,
                c.form,
                c.filing_date,
                c.section,
                c.chunk_index,
                c.token_count,
                c.text,
                json.dumps(c.payload()),
            )
            for c in chunks
        ]
        self._conn.executemany(
            """
            INSERT INTO chunks (
                chunk_id, accession, ticker, form, filing_date, section,
                chunk_index, token_count, text, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chunk_id) DO UPDATE SET text=excluded.text, payload_json=excluded.payload_json
            """,
            rows,
        )
        self._conn.commit()

    def filing_count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS n FROM filings").fetchone()
        return int(row["n"]) if row else 0

    def chunk_count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS n FROM chunks").fetchone()
        return int(row["n"]) if row else 0

    def close(self) -> None:
        self._conn.close()
