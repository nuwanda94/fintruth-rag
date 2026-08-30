"""Minimal truth-seeking loop: retrieve → grade → generate or refuse.

LangGraph is optional. The default ``TruthSeekingGraph`` is a typed state
machine with the same node contract so the loop is testable offline without
installing the extra. When ``langgraph`` is present, ``compile_langgraph``
wraps the same nodes.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Literal

from fintruth.config import Settings, get_settings
from fintruth.generation.chain import GroundedAnswer, generate_answer, should_refuse
from fintruth.generation.prompts import REFUSAL_PREFIX
from fintruth.retrieval.filters import RetrievalFilters
from fintruth.retrieval.hybrid import HybridRetriever, RetrievedChunk, RetrieveTrace

Decision = Literal["generate", "refuse"]


@dataclass(slots=True)
class AgentState:
    """Shared state passed through retrieve → grade → generate/refuse."""

    question: str
    filters: RetrievalFilters = field(default_factory=RetrievalFilters)
    chunks: list[RetrievedChunk] = field(default_factory=list)
    grade_reason: str | None = None
    decision: Decision | None = None
    answer: GroundedAnswer | None = None
    trace: RetrieveTrace | None = None
    extractive: bool = True


@dataclass(slots=True)
class GraphRun:
    """Interview-facing result of one graph invocation."""

    state: AgentState
    path: list[str]
    latency_ms: float = 0.0

    @property
    def answer(self) -> GroundedAnswer:
        if self.state.answer is None:
            raise RuntimeError("graph did not produce an answer")
        return self.state.answer


def retrieve_node(state: AgentState, retriever: HybridRetriever, *, final_k: int | None = None) -> AgentState:
    """Pull hybrid evidence for the question."""
    chunks = retriever.retrieve(state.question, filters=state.filters, final_k=final_k)
    state.chunks = chunks
    state.trace = retriever.last_trace
    return state


def grade_node(state: AgentState) -> AgentState:
    """Decide generate vs refuse from retrieval quality gates."""
    reason = should_refuse(state.chunks, state.question)
    state.grade_reason = reason
    state.decision = "refuse" if reason else "generate"
    return state


def refuse_node(state: AgentState) -> AgentState:
    """Emit a structured refusal without calling an LLM."""
    reason = state.grade_reason or "insufficient evidence"
    state.answer = GroundedAnswer(
        question=state.question,
        answer=f"{REFUSAL_PREFIX} {reason}",
        refused=True,
        refusal_reason=reason,
        citations=[],
        chunks=state.chunks,
        mode="graph-refuse",
    )
    return state


def generate_node(state: AgentState, *, settings: Settings | None = None) -> AgentState:
    """Produce a grounded answer; still gated inside generate_answer."""
    use_llm = False if state.extractive else None
    state.answer = generate_answer(
        state.question,
        state.chunks,
        use_llm=use_llm,
        settings=settings,
    )
    return state


class TruthSeekingGraph:
    """Retrieve → grade → (generate | refuse). No hidden tool use."""

    def __init__(
        self,
        retriever: HybridRetriever,
        *,
        settings: Settings | None = None,
        extractive: bool = True,
        final_k: int | None = None,
    ) -> None:
        self.retriever = retriever
        self.settings = settings or get_settings()
        self.extractive = extractive
        self.final_k = final_k

    def invoke(
        self,
        question: str,
        filters: RetrievalFilters | None = None,
    ) -> GraphRun:
        """Run the three-node loop and return path + grounded answer."""
        started = time.perf_counter()
        state = AgentState(
            question=question,
            filters=filters or RetrievalFilters(),
            extractive=self.extractive,
        )
        path = ["retrieve"]
        retrieve_node(state, self.retriever, final_k=self.final_k)
        path.append("grade")
        grade_node(state)
        if state.decision == "refuse":
            path.append("refuse")
            refuse_node(state)
        else:
            path.append("generate")
            generate_node(state, settings=self.settings)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return GraphRun(state=state, path=path, latency_ms=elapsed_ms)


def compile_langgraph(graph: TruthSeekingGraph) -> Any:
    """Optional LangGraph StateGraph using the same nodes.

    Raises ImportError if langgraph is not installed. Kept out of the default
    path so tests stay dependency-light.
    """
    from langgraph.graph import END, START, StateGraph

    def _retrieve(raw: dict[str, Any]) -> dict[str, Any]:
        state = raw["state"]
        retrieve_node(state, graph.retriever, final_k=graph.final_k)
        return raw

    def _grade(raw: dict[str, Any]) -> dict[str, Any]:
        grade_node(raw["state"])
        return raw

    def _route(raw: dict[str, Any]) -> str:
        return "refuse" if raw["state"].decision == "refuse" else "generate"

    def _refuse(raw: dict[str, Any]) -> dict[str, Any]:
        refuse_node(raw["state"])
        return raw

    def _generate(raw: dict[str, Any]) -> dict[str, Any]:
        generate_node(raw["state"], settings=graph.settings)
        return raw

    builder = StateGraph(dict)
    builder.add_node("retrieve", _retrieve)
    builder.add_node("grade", _grade)
    builder.add_node("refuse", _refuse)
    builder.add_node("generate", _generate)
    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", "grade")
    builder.add_conditional_edges("grade", _route, {"refuse": "refuse", "generate": "generate"})
    builder.add_edge("refuse", END)
    builder.add_edge("generate", END)
    return builder.compile()
