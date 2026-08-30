"""Grounded generation: parse citations, refuse on weak evidence.

Default path is extractive (no LLM) so the retrieve → answer loop works
offline. When ``XAI_API_KEY`` is set, ``generate_answer`` may call Grok
and then re-apply the same citation / refusal gates.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from fintruth.config import Settings, get_settings
from fintruth.generation.prompts import REFUSAL_PREFIX, build_messages
from fintruth.retrieval.hybrid import RetrievedChunk

_CITE = re.compile(r"\[(\d+)\]")
_TOKEN = re.compile(r"[a-z0-9$%]+", re.I)
_TICKER = re.compile(
    r"\b(AAPL|MSFT|GOOGL|AMZN|META|NVDA|JPM|XOM|UNH|JNJ|TSLA|BRK)\b",
    re.I,
)
_YEAR = re.compile(r"\b(?:fy|fiscal\s+)?((?:19|20)\d{2})\b", re.I)
_EXACT_FACT = re.compile(
    r"\b(exact|unit volume|units?|deliveries|how many)\b",
    re.I,
)

DEFAULT_MIN_SCORE = 0.012
DEFAULT_MIN_OVERLAP = 1

XAI_CHAT_URL = "https://api.x.ai/v1/chat/completions"


@dataclass(slots=True)
class Citation:
    """Pointer from an answer span back to a retrieved chunk."""

    index: int
    chunk_id: str
    ticker: str
    form: str
    section: str
    filing_date: str

    def format_line(self) -> str:
        """Interview-facing footnote line."""
        return (
            f"[{self.index}] {self.ticker} {self.form} {self.section} "
            f"{self.filing_date} ({self.chunk_id})"
        )


@dataclass(slots=True)
class GroundedAnswer:
    """Structured generation result handed to CLI / later UI."""

    question: str
    answer: str
    refused: bool
    refusal_reason: str | None
    citations: list[Citation] = field(default_factory=list)
    chunks: list[RetrievedChunk] = field(default_factory=list)
    mode: str = "extractive"

    def sources_block(self) -> str:
        """Render a Sources footer from parsed citations."""
        if not self.citations:
            return ""
        lines = ["Sources:"] + [c.format_line() for c in self.citations]
        return "\n".join(lines)


def parse_citations(text: str, chunks: list[RetrievedChunk]) -> list[Citation]:
    """Extract [n] markers and map them onto retrieved chunks (1-indexed)."""
    seen: set[int] = set()
    out: list[Citation] = []
    for raw in _CITE.findall(text):
        idx = int(raw)
        if idx in seen or idx < 1 or idx > len(chunks):
            continue
        seen.add(idx)
        chunk = chunks[idx - 1]
        out.append(
            Citation(
                index=idx,
                chunk_id=chunk.chunk_id,
                ticker=str(chunk.payload.get("ticker", "")),
                form=str(chunk.payload.get("form", "")),
                section=str(chunk.payload.get("section", "")),
                filing_date=str(chunk.payload.get("filing_date", "")),
            )
        )
    return out


def format_citation_footer(citations: list[Citation]) -> str:
    """Stable Sources block used by extractive and LLM post-process paths."""
    if not citations:
        return ""
    return "Sources:\n" + "\n".join(c.format_line() for c in citations)


def attach_sources(answer: str, citations: list[Citation]) -> str:
    """Append a Sources footer if the body does not already include one."""
    if not citations or re.search(r"(?im)^sources:", answer):
        return answer
    return answer.rstrip() + "\n\n" + format_citation_footer(citations)


def parse_model_output(
    text: str, chunks: list[RetrievedChunk]
) -> tuple[bool, str, str | None, list[Citation]]:
    """Split a model reply into refusal vs cited answer."""
    stripped = text.strip()
    if stripped.upper().startswith(REFUSAL_PREFIX):
        reason = stripped[len(REFUSAL_PREFIX) :].strip() or "insufficient evidence"
        return True, stripped, reason, []
    cites = parse_citations(stripped, chunks)
    return False, stripped, None, cites


_NAME_TO_TICKER = {
    "TESLA": "TSLA",
    "APPLE": "AAPL",
    "MICROSOFT": "MSFT",
    "ALPHABET": "GOOGL",
    "GOOGLE": "GOOGL",
    "AMAZON": "AMZN",
    "META": "META",
    "FACEBOOK": "META",
    "NVIDIA": "NVDA",
    "JPMORGAN": "JPM",
    "EXXON": "XOM",
    "UNITEDHEALTH": "UNH",
    "JOHNSON": "JNJ",
    "BERKSHIRE": "BRK",
}


def mentioned_tickers(question: str) -> list[str]:
    """Tickers explicitly named in the question (interview-max universe)."""
    seen: list[str] = []
    upper = question.upper()
    for match in _TICKER.findall(upper):
        if match not in seen:
            seen.append(match)
    for name, ticker in _NAME_TO_TICKER.items():
        if re.search(r"\b" + name + r"\b", upper) and ticker not in seen:
            seen.append(ticker)
    return seen


def question_years(question: str) -> list[str]:
    """Fiscal or calendar years mentioned in the question text."""
    seen: list[str] = []
    for match in _YEAR.finditer(question or ""):
        year = match.group(1)
        if year not in seen:
            seen.append(year)
    return seen


def asks_exact_figure(question: str) -> bool:
    """True when the asker wants a precise count/volume, not qualitative MD&A."""
    return bool(_EXACT_FACT.search(question or ""))


def _overlap_count(question: str, text: str) -> int:
    q = set(_TOKEN.findall(question.lower()))
    t = set(_TOKEN.findall(text.lower()))
    stop = {"the", "a", "an", "of", "and", "or", "in", "to", "for", "what", "does", "do"}
    return len((q - stop) & t)


def _evidence_mentions_year(chunks: list[RetrievedChunk], years: list[str]) -> bool:
    """Period must appear in chunk *text*, not merely in filing_date."""
    blob = " ".join(c.text for c in chunks)
    return any(year in blob for year in years)


def should_refuse(
    chunks: list[RetrievedChunk],
    question: str,
    *,
    min_score: float = DEFAULT_MIN_SCORE,
    min_overlap: int = DEFAULT_MIN_OVERLAP,
) -> str | None:
    """Return a refusal reason, or None if generation may proceed."""
    if not chunks:
        return "no retrieved evidence"
    wanted = mentioned_tickers(question)
    if wanted:
        present = {str(c.payload.get("ticker", "")).upper() for c in chunks}
        missing = [tkr for tkr in wanted if tkr not in present]
        if missing:
            return "missing evidence for ticker(s) " + ", ".join(missing)
    best = max(c.score for c in chunks)
    if best < min_score:
        return f"top retrieval score {best:.4f} below {min_score:.4f}"
    if not any(_overlap_count(question, c.text) >= min_overlap for c in chunks):
        return "retrieved chunks do not overlap the question terms"
    if asks_exact_figure(question):
        years = question_years(question)
        if years and not _evidence_mentions_year(chunks, years):
            return "asked period " + ", ".join(years) + " not present in retrieved evidence"
    return None


def extractive_answer(question: str, chunks: list[RetrievedChunk]) -> GroundedAnswer:
    """Offline grounded path: quote supporting snippets with [n] citations."""
    reason = should_refuse(chunks, question)
    if reason:
        text = f"{REFUSAL_PREFIX} {reason}"
        return GroundedAnswer(
            question=question,
            answer=text,
            refused=True,
            refusal_reason=reason,
            citations=[],
            chunks=chunks,
            mode="extractive",
        )

    lines: list[str] = []
    used: list[int] = []
    for i, chunk in enumerate(chunks, start=1):
        if _overlap_count(question, chunk.text) < DEFAULT_MIN_OVERLAP:
            continue
        snippet = chunk.text.strip()
        if len(snippet) > 320:
            snippet = snippet[:317] + "..."
        lines.append(f"{snippet} [{i}]")
        used.append(i)
        if len(used) >= 3:
            break
    if not lines:
        reason = "no overlapping evidence after filtering"
        text = f"{REFUSAL_PREFIX} {reason}"
        return GroundedAnswer(
            question=question,
            answer=text,
            refused=True,
            refusal_reason=reason,
            citations=[],
            chunks=chunks,
            mode="extractive",
        )
    body = "Based on the retrieved SEC excerpts:\n" + "\n".join(f"- {line}" for line in lines)
    cites = parse_citations(body, chunks)
    answer = attach_sources(body, cites)
    return GroundedAnswer(
        question=question,
        answer=answer,
        refused=False,
        refusal_reason=None,
        citations=cites,
        chunks=chunks,
        mode="extractive",
    )


def complete_with_grok(
    messages: list[dict[str, str]],
    *,
    settings: Settings | None = None,
    timeout_s: float = 30.0,
) -> str | None:
    """Call xAI chat completions. Returns None when no key or the request fails."""
    settings = settings or get_settings()
    if not settings.xai_api_key:
        return None
    payload = {
        "model": settings.xai_model,
        "messages": messages,
        "temperature": 0.0,
    }
    raw = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        XAI_CHAT_URL,
        data=raw,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.xai_api_key}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None
    choices = body.get("choices") or []
    if not choices:
        return None
    message = choices[0].get("message") or {}
    content = message.get("content")
    return str(content) if content else None


def _finalize_llm_answer(
    question: str,
    chunks: list[RetrievedChunk],
    model_text: str,
) -> GroundedAnswer:
    """Apply citation + refusal gates to a model completion."""
    pre = should_refuse(chunks, question)
    if pre:
        text = f"{REFUSAL_PREFIX} {pre}"
        return GroundedAnswer(
            question=question,
            answer=text,
            refused=True,
            refusal_reason=pre,
            citations=[],
            chunks=chunks,
            mode="llm",
        )
    refused, answer, reason, cites = parse_model_output(model_text, chunks)
    if refused:
        return GroundedAnswer(
            question=question,
            answer=answer,
            refused=True,
            refusal_reason=reason,
            citations=[],
            chunks=chunks,
            mode="llm",
        )
    if not cites:
        reason = "model answer lacked citations"
        text = f"{REFUSAL_PREFIX} {reason}"
        return GroundedAnswer(
            question=question,
            answer=text,
            refused=True,
            refusal_reason=reason,
            citations=[],
            chunks=chunks,
            mode="llm",
        )
    answer = attach_sources(answer, cites)
    return GroundedAnswer(
        question=question,
        answer=answer,
        refused=False,
        refusal_reason=None,
        citations=cites,
        chunks=chunks,
        mode="llm",
    )


def generate_answer(
    question: str,
    chunks: list[RetrievedChunk],
    *,
    model_text: str | None = None,
    use_llm: bool | None = None,
    settings: Settings | None = None,
) -> GroundedAnswer:
    """Build a GroundedAnswer from retrieve hits.

    Pass ``model_text`` when an LLM already produced a completion. Otherwise
    fall back to extractive mode, unless ``use_llm`` is true or an API key is
    present and ``use_llm`` was left as None.
    """
    settings = settings or get_settings()
    if model_text is None:
        should_call = use_llm if use_llm is not None else bool(settings.xai_api_key)
        if should_call:
            model_text = complete_with_grok(build_messages(question, chunks), settings=settings)
    if model_text is None:
        return extractive_answer(question, chunks)
    return _finalize_llm_answer(question, chunks, model_text)


def prompt_for(question: str, chunks: list[RetrievedChunk]) -> list[dict[str, str]]:
    """Public helper so callers can inspect the grounded prompt."""
    return build_messages(question, chunks)
