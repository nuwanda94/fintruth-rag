"""Section-aware parser for SEC HTML (MD&A, Risk Factors, key notes)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Item headings we keep in the interview-max corpus.
TARGET_SECTIONS: dict[str, tuple[str, ...]] = {
    "mda": (
        r"item\s*7[\.\s].*management.?s?\s+discussion",
        r"item\s*2[\.\s].*management.?s?\s+discussion",
    ),
    "risk_factors": (
        r"item\s*1a[\.\s].*risk\s+factors",
        r"item\s*1a[\.\s]",
    ),
    "business": (r"item\s*1[\.\s].*business",),
    "legal_proceedings": (r"item\s*3[\.\s].*legal",),
    "notes": (r"notes?\s+to\s+(the\s+)?consolidat", r"item\s*8[\.\s].*financial\s+statements"),
}

_HEADING_RE = re.compile(
    r"^(item\s+\d+[a-z]?\b.*|notes?\s+to\s+.+)$",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ParsedSection:
    """One extracted section from a filing."""

    name: str
    title: str
    text: str
    start_char: int
    end_char: int


def _html_to_text(html: str) -> str:
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("beautifulsoup4 is required to parse filings") from exc

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _match_section(line: str) -> str | None:
    for name, patterns in TARGET_SECTIONS.items():
        for pat in patterns:
            if re.search(pat, line, flags=re.IGNORECASE):
                return name
    return None


def parse_filing_html(path: Path | str, html: str | None = None) -> list[ParsedSection]:
    """Extract target sections from a filing HTML file or raw HTML string."""
    if html is None:
        html = Path(path).read_text(encoding="utf-8", errors="replace")
    text = _html_to_text(html)
    lines = text.split("\n")

    headings: list[tuple[int, str, str]] = []
    cursor = 0
    for line in lines:
        name = _match_section(line) if _HEADING_RE.match(line.strip()) or _match_section(line) else None
        if name:
            headings.append((cursor, name, line.strip()))
        cursor += len(line) + 1

    sections: list[ParsedSection] = []
    for i, (start, name, title) in enumerate(headings):
        end = headings[i + 1][0] if i + 1 < len(headings) else len(text)
        body = text[start:end].strip()
        if len(body) < 200:
            continue
        sections.append(
            ParsedSection(name=name, title=title[:200], text=body, start_char=start, end_char=end)
        )

    if not sections:
        logger.warning("No target sections found in %s; storing full text as 'full_filing'", path)
        if text.strip():
            sections.append(
                ParsedSection(
                    name="full_filing",
                    title="full_filing",
                    text=text,
                    start_char=0,
                    end_char=len(text),
                )
            )
    return sections
