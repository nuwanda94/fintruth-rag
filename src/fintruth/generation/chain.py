"""Grounded generation: parse citations, refuse on weak evidence.

Default path is extractive (no LLM) so the retrieve → answer loop works
offline. When ``XAI_API_KEY`` is set, ``generate_answer`` may call Grok
and then re-apply the same citation / refusal gates.

Implementation is split across ``citations``, ``refuse``, ``units``,
``usage``, and ``generate`` so each module stays reviewable.
"""

from fintruth.generation.citations import (
    Citation,
    GroundedAnswer,
    attach_sources,
    format_citation_footer,
    parse_citations,
    parse_model_output,
)
from fintruth.generation.generate import (
    complete_with_grok,
    complete_with_grok_detailed,
    extractive_answer,
    generate_answer,
    prompt_for,
)
from fintruth.generation.refuse import (
    DEFAULT_MIN_OVERLAP,
    DEFAULT_MIN_SCORE,
    asks_exact_figure,
    mentioned_tickers,
    missing_cited_tickers,
    question_years,
    select_quote_indices,
    should_refuse,
)
from fintruth.generation.units import asks_unit_volume, evidence_has_unit_quantity
from fintruth.generation.usage import TokenUsage, estimate_tokens, measure_usage, usage_from_api

__all__ = [
    "Citation",
    "DEFAULT_MIN_OVERLAP",
    "DEFAULT_MIN_SCORE",
    "GroundedAnswer",
    "TokenUsage",
    "asks_exact_figure",
    "asks_unit_volume",
    "attach_sources",
    "complete_with_grok",
    "complete_with_grok_detailed",
    "estimate_tokens",
    "evidence_has_unit_quantity",
    "extractive_answer",
    "format_citation_footer",
    "generate_answer",
    "measure_usage",
    "mentioned_tickers",
    "missing_cited_tickers",
    "parse_citations",
    "parse_model_output",
    "prompt_for",
    "question_years",
    "select_quote_indices",
    "should_refuse",
    "usage_from_api",
]
