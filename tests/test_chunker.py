"""Smoke tests for section chunking (no network)."""

from pathlib import Path

from fintruth.ingestion.chunker import chunk_section
from fintruth.ingestion.downloader import FilingRef
from fintruth.ingestion.parser import ParsedSection, parse_filing_html

# Bodies must exceed parser.min_section_chars (200) or headings are dropped.
_RISK = (
    "We face intense competition in every market. A sustained decline in demand "
    "could materially affect results of operations, cash flows, and market share. "
    "Competitors include other smartphone, wearables, and services vendors worldwide. "
    "Pricing pressure and rapid product cycles remain material risk factors."
)
_MDA = (
    "Revenue increased year over year driven by services mix and installed base. "
    "Liquidity remains sufficient for planned operations, capital returns, and R&D. "
    "iPhone net sales were the largest product category discussed in this MD&A. "
    "Management monitors gross margin, channel inventory, and foreign-exchange effects."
)

SAMPLE_HTML = f"""
<html><body>
<p>ITEM 1A. RISK FACTORS</p>
<p>{_RISK}</p>
<p>ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS</p>
<p>{_MDA}</p>
</body></html>
"""


def test_parse_extracts_target_sections() -> None:
    sections = parse_filing_html(Path("memory.html"), html=SAMPLE_HTML)
    names = {s.name for s in sections}
    assert "risk_factors" in names
    assert "mda" in names
    assert "full_filing" not in names


def test_chunk_section_attaches_metadata() -> None:
    section = ParsedSection(
        name="risk_factors",
        title="ITEM 1A. RISK FACTORS",
        text="Competition is intense. " * 80,
        start_char=0,
        end_char=100,
    )
    filing = FilingRef(
        ticker="AAPL",
        cik="320193",
        form="10-K",
        filing_date="2024-11-01",
        accession="0000320193-24-000123",
    )
    chunks = chunk_section(section, filing)
    assert chunks
    assert chunks[0].ticker == "AAPL"
    assert chunks[0].section == "risk_factors"
    assert chunks[0].chunk_id.startswith("AAPL:")
