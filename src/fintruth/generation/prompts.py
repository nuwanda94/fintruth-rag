"""Grounded-answer prompts and evidence formatting."""

from __future__ import annotations

from fintruth.retrieval.hybrid import RetrievedChunk

SYSTEM_PROMPT = """You are FinTruth, a SEC-grounded financial research assistant.

Rules:
- Answer ONLY from the numbered evidence blocks. Do not use outside knowledge.
- Cite every factual claim with bracketed evidence ids like [1] or [1][2].
- If the evidence is missing, conflicting, or too weak to support an answer,
  refuse. Use exactly: REFUSAL: followed by a one-sentence reason.
- Never invent numbers, dates, ticker facts, or section names.
- Prefer the most recent filing_date when evidence disagrees.
- Do not emit a Sources footer; the system will attach structured citations.
"""

USER_TEMPLATE = """Question: {question}

Evidence:
{evidence}

Write a grounded answer with citations, or REFUSAL: <reason>."""

REFUSAL_PREFIX = "REFUSAL:"


def format_evidence_block(chunks: list[RetrievedChunk]) -> str:
    """Render retrieved chunks as numbered blocks the model must cite."""
    if not chunks:
        return "(no evidence retrieved)"
    blocks: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        ticker = chunk.payload.get("ticker", "?")
        form = chunk.payload.get("form", "?")
        section = chunk.payload.get("section", "?")
        filed = chunk.payload.get("filing_date", "?")
        header = f"[{i}] {ticker} {form} {section} filed {filed} (score={chunk.score:.4f})"
        body = chunk.text.strip() or "(empty chunk)"
        blocks.append(f"{header}\n{body}")
    return "\n\n".join(blocks)


def build_messages(question: str, chunks: list[RetrievedChunk]) -> list[dict[str, str]]:
    """Chat messages for a Grok (or compatible) completion."""
    user = USER_TEMPLATE.format(
        question=question.strip(),
        evidence=format_evidence_block(chunks),
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
