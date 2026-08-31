"""Offline tests for retrieve → grade → generate/refuse."""

from fintruth.agent.graph import TruthSeekingGraph, grade_node, retrieve_node
from fintruth.agent import AgentState
from fintruth.eval.runner import DEMO_CORPUS, build_retriever
from fintruth.generation.prompts import REFUSAL_PREFIX
from fintruth.retrieval.filters import RetrievalFilters


def _graph() -> TruthSeekingGraph:
    return TruthSeekingGraph(build_retriever(DEMO_CORPUS), extractive=True, final_k=4)


def test_graph_generates_on_supported_apple_question() -> None:
    run = _graph().invoke("What competition risks does Apple disclose?")
    assert run.path == ["retrieve", "grade", "generate"]
    assert run.state.decision == "generate"
    assert not run.answer.refused
    assert run.answer.citations
    assert "[1]" in run.answer.answer


def test_graph_refuses_out_of_corpus() -> None:
    run = _graph().invoke("What litigation contingencies did Tesla disclose in 2019?")
    assert run.path[0] == "retrieve"
    assert run.path[-1] in {"refuse", "generate"}
    # Tesla is not in DEMO_CORPUS; grade or extractive gates should refuse.
    if run.path[-1] == "refuse":
        assert run.answer.refused
        assert run.answer.answer.startswith(REFUSAL_PREFIX)
    else:
        # Weak overlap may still reach generate, which must then refuse.
        assert run.answer.refused


def test_grade_node_refuses_empty_chunks() -> None:
    state = AgentState(question="anything")
    grade_node(state)
    assert state.decision == "refuse"
    assert state.grade_reason == "no retrieved evidence"


def test_retrieve_respects_ticker_filter() -> None:
    graph = _graph()
    state = AgentState(
        question="competition",
        filters=RetrievalFilters(tickers=["AAPL"]),
    )
    retrieve_node(state, graph.retriever, final_k=4)
    assert state.chunks
    assert all(c.payload.get("ticker") == "AAPL" for c in state.chunks)


def test_graph_records_latency() -> None:
    run = _graph().invoke("What competition risks does Apple disclose?")
    assert run.latency_ms >= 0.0
    assert run.retrieve_ms >= 0.0
    assert run.generate_ms >= 0.0
    assert run.state.trace is not None
    assert run.state.trace.latency_ms >= 0.0
    assert run.state.trace.n_returned >= 1
    assert run.usage.total_tokens > 0
    assert run.usage.source == "estimate"
