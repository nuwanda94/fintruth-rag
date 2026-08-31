"""Token estimate + API usage parse + graph stage latency."""

from fintruth.agent.graph import TruthSeekingGraph
from fintruth.eval.runner import DEMO_CORPUS, build_retriever
from fintruth.generation.chain import generate_answer
from fintruth.generation.usage import estimate_tokens, measure_usage, usage_from_api
from fintruth.retrieval.hybrid import RetrievedChunk


def test_estimate_tokens_empty_and_short() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("abcdefgh") == 2


def test_usage_from_api_prefers_provider_counts() -> None:
    parsed = usage_from_api({"usage": {"prompt_tokens": 12, "completion_tokens": 4, "total_tokens": 16}})
    assert parsed is not None
    assert parsed.source == "api"
    assert parsed.prompt_tokens == 12
    assert parsed.completion_tokens == 4
    assert parsed.total_tokens == 16
    assert usage_from_api({}) is None
    assert usage_from_api({"usage": {}}) is None


def test_extractive_answer_attaches_estimated_usage() -> None:
    chunk = RetrievedChunk(
        chunk_id="AAPL:risk:0",
        text="Apple faces intense competition in smartphones, wearables, and services.",
        score=0.05,
        dense_rank=1,
        sparse_rank=1,
        payload={
            "text": "Apple faces intense competition in smartphones, wearables, and services.",
            "ticker": "AAPL",
            "form": "10-K",
            "section": "risk_factors",
            "filing_date": "2024-11-01",
        },
    )
    result = generate_answer(
        "What competition risks does Apple disclose?",
        [chunk],
        use_llm=False,
    )
    assert not result.refused
    assert result.usage.source == "estimate"
    assert result.usage.prompt_tokens > 0
    assert result.usage.completion_tokens > 0
    assert result.usage.total_tokens == result.usage.prompt_tokens + result.usage.completion_tokens
    expected = measure_usage(result.question, result.chunks, result.answer)
    assert result.usage.prompt_tokens == expected.prompt_tokens


def test_graph_exposes_stage_latency_and_usage() -> None:
    graph = TruthSeekingGraph(build_retriever(DEMO_CORPUS), extractive=True, final_k=4)
    run = graph.invoke("What competition risks does Apple disclose?")
    assert run.latency_ms >= 0.0
    assert run.retrieve_ms >= 0.0
    assert run.generate_ms >= 0.0
    assert run.usage.total_tokens > 0
    assert run.answer.usage.total_tokens == run.usage.total_tokens
