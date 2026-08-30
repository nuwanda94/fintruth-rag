"""SEC filing download, section parse, and chunking."""

from fintruth.ingestion.chunker import Chunk, chunk_section
from fintruth.ingestion.downloader import FilingRef, download_filings
from fintruth.ingestion.parser import ParsedSection, parse_filing_html
from fintruth.ingestion.preflight import PreflightResult, run_preflight

__all__ = [
    "Chunk",
    "FilingRef",
    "ParsedSection",
    "PreflightResult",
    "chunk_section",
    "download_filings",
    "parse_filing_html",
    "run_preflight",
]
