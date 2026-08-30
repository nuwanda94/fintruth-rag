"""Extractive and optional Grok generation with post-cite gates."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from fintruth.config import Settings, get_settings
from fintruth.generation.citations import (
    GroundedAnswer,
    attach_sources,
    parse_citations,
    parse_model_output,
)
from fintruth.generation.prompts import REFUSAL_PREFIX, build_messages
from fintruth.generation.refuse import missing_cited_tickers, select_quote_indices, should_refuse
from fintruth.retrieval.hybrid import RetrievedChunk

XAI_CHAT_URL = "https://api.x.ai/v1/chat/completions"


def _refuse(question: str, chunks: list[RetrievedChunk], reason: str, mode: str) -> GroundedAnswer:
    return GroundedAnswer(
        question=question,
        answer=f"{REFUSAL_PREFIX} {reason}",
        refused=True,
        refusal_reason=reason,
        citations=[],
        chunks=chunks,
        mode=mode,
    )


def extractive_answer(question: str, chunks: list[RetrievedChunk]) -> GroundedAnswer:
    """Offline grounded path: quote supporting snippets with [n] citations."""
    reason = should_refuse(chunks, question)
    if reason:
        return _refuse(question, chunks, reason, "extractive")

    used = select_quote_indices(question, chunks, limit=3)
    if not used:
        return _refuse(question, chunks, "no overlapping evidence after filtering", "extractive")

    lines: list[str] = []
    for i in used:
        snippet = chunks[i - 1].text.strip()
        if len(snippet) > 320:
            snippet = snippet[:317] + "..."
        lines.append(f"{snippet} [{i}]")
    body = "Based on the retrieved SEC excerpts:\n" + "\n".join(f"- {line}" for line in lines)
    cites = parse_citations(body, chunks)
    missing = missing_cited_tickers(question, cites)
    if missing:
        return _refuse(
            question,
            chunks,
            "citations omit ticker(s) " + ", ".join(missing),
            "extractive",
        )
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
        return _refuse(question, chunks, pre, "llm")
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
        return _refuse(question, chunks, "model answer lacked citations", "llm")
    missing = missing_cited_tickers(question, cites)
    if missing:
        return _refuse(
            question,
            chunks,
            "citations omit ticker(s) " + ", ".join(missing),
            "llm",
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
