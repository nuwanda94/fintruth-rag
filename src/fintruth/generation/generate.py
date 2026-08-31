"""Extractive and optional Grok generation with post-cite gates."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from fintruth.config import Settings, get_settings
from fintruth.generation.citations import (
    GroundedAnswer,
    attach_sources,
    parse_citations,
    parse_model_output,
)
from fintruth.generation.prompts import REFUSAL_PREFIX, build_messages
from fintruth.generation.refuse import missing_cited_tickers, select_quote_indices, should_refuse
from fintruth.generation.usage import TokenUsage, measure_usage, usage_from_api
from fintruth.retrieval.hybrid import RetrievedChunk

XAI_CHAT_URL = "https://api.x.ai/v1/chat/completions"


def _with_usage(
    answer: GroundedAnswer,
    *,
    api_usage: TokenUsage | None = None,
) -> GroundedAnswer:
    answer.usage = measure_usage(
        answer.question,
        answer.chunks,
        answer.answer,
        api_usage=api_usage,
    )
    return answer


def _refuse(
    question: str,
    chunks: list[RetrievedChunk],
    reason: str,
    mode: str,
    *,
    api_usage: TokenUsage | None = None,
) -> GroundedAnswer:
    return _with_usage(
        GroundedAnswer(
            question=question,
            answer=f"{REFUSAL_PREFIX} {reason}",
            refused=True,
            refusal_reason=reason,
            citations=[],
            chunks=chunks,
            mode=mode,
        ),
        api_usage=api_usage,
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
    return _with_usage(
        GroundedAnswer(
            question=question,
            answer=answer,
            refused=False,
            refusal_reason=None,
            citations=cites,
            chunks=chunks,
            mode="extractive",
        )
    )


def complete_with_grok(
    messages: list[dict[str, str]],
    *,
    settings: Settings | None = None,
    timeout_s: float = 30.0,
) -> str | None:
    """Call xAI chat completions. Returns None when no key or the request fails."""
    text, _usage = complete_with_grok_detailed(
        messages, settings=settings, timeout_s=timeout_s
    )
    return text


def complete_with_grok_detailed(
    messages: list[dict[str, str]],
    *,
    settings: Settings | None = None,
    timeout_s: float = 30.0,
) -> tuple[str | None, TokenUsage | None]:
    """Like ``complete_with_grok`` but also returns API token usage when present."""
    settings = settings or get_settings()
    if not settings.xai_api_key:
        return None, None
    payload: dict[str, Any] = {
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
        return None, None
    usage = usage_from_api(body if isinstance(body, dict) else None)
    choices = body.get("choices") or []
    if not choices:
        return None, usage
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not content:
        return None, usage
    return str(content), usage


def _finalize_llm_answer(
    question: str,
    chunks: list[RetrievedChunk],
    model_text: str,
    *,
    api_usage: TokenUsage | None = None,
) -> GroundedAnswer:
    """Apply citation + refusal gates to a model completion."""
    pre = should_refuse(chunks, question)
    if pre:
        return _refuse(question, chunks, pre, "llm", api_usage=api_usage)
    refused, answer, reason, cites = parse_model_output(model_text, chunks)
    if refused:
        return _with_usage(
            GroundedAnswer(
                question=question,
                answer=answer,
                refused=True,
                refusal_reason=reason,
                citations=[],
                chunks=chunks,
                mode="llm",
            ),
            api_usage=api_usage,
        )
    if not cites:
        return _refuse(question, chunks, "model answer lacked citations", "llm", api_usage=api_usage)
    missing = missing_cited_tickers(question, cites)
    if missing:
        return _refuse(
            question,
            chunks,
            "citations omit ticker(s) " + ", ".join(missing),
            "llm",
            api_usage=api_usage,
        )
    answer = attach_sources(answer, cites)
    return _with_usage(
        GroundedAnswer(
            question=question,
            answer=answer,
            refused=False,
            refusal_reason=None,
            citations=cites,
            chunks=chunks,
            mode="llm",
        ),
        api_usage=api_usage,
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
    api_usage: TokenUsage | None = None
    if model_text is None:
        should_call = use_llm if use_llm is not None else bool(settings.xai_api_key)
        if should_call:
            model_text, api_usage = complete_with_grok_detailed(
                build_messages(question, chunks), settings=settings
            )
    if model_text is None:
        return extractive_answer(question, chunks)
    return _finalize_llm_answer(question, chunks, model_text, api_usage=api_usage)


def prompt_for(question: str, chunks: list[RetrievedChunk]) -> list[dict[str, str]]:
    """Public helper so callers can inspect the grounded prompt."""
    return build_messages(question, chunks)
