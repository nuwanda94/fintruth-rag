"""Streamlit evidence demo: answer, chunks, scores, citations, refusal.

Run:
    uv run --extra ui streamlit run src/fintruth/ui/app.py
"""

from __future__ import annotations

from functools import lru_cache

from fintruth.agent.graph import TruthSeekingGraph
from fintruth.eval.runner import DEMO_CORPUS, build_retriever
from fintruth.retrieval.filters import RetrievalFilters

_EXAMPLES = {
    "Easy — AAPL competition": "What competition risks does Apple disclose?",
    "Hard refuse — TSLA": "Did Tesla disclose Cybertruck unit deliveries in its latest 10-K?",
    "Period refuse — FY2012 units": "What was Apple's exact FY2012 greater-China iPhone unit volume?",
    "Compare — AAPL vs MSFT": "Compare Apple iPhone revenue commentary with Microsoft Azure growth commentary.",
}


@lru_cache(maxsize=1)
def _demo_graph() -> TruthSeekingGraph:
    retriever = build_retriever(DEMO_CORPUS)
    return TruthSeekingGraph(retriever, extractive=True, final_k=6)


def _run_query(question: str, ticker: str, section: str, as_of: str):
    filters = RetrievalFilters(
        tickers=[ticker] if ticker and ticker != "ALL" else [],
        sections=[section] if section and section != "ALL" else [],
        as_of=as_of or None,
    )
    return _demo_graph().invoke(question, filters=filters)


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="FinTruth RAG", layout="wide")
    st.title("FinTruth RAG")
    st.caption("SEC-grounded retrieve → grade → generate or refuse (demo corpus).")

    with st.sidebar:
        st.header("Filters")
        ticker = st.selectbox("Ticker", ["ALL", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "JPM", "XOM", "UNH", "JNJ"])
        section = st.selectbox("Section", ["ALL", "risk_factors", "mda"])
        as_of = st.text_input("As-of date (YYYY-MM-DD)", value="")
        st.subheader("Walkthrough prompts")
        for label, prompt in _EXAMPLES.items():
            if st.button(label):
                st.session_state["question"] = prompt
        st.markdown(
            "Demo corpus is the offline fixture from `evals` — not live EDGAR. "
            "Hash embeddings + lexical rerank are wiring, not quality claims."
        )

    question = st.text_input(
        "Question",
        value=st.session_state.get("question", "What competition risks does Apple disclose?"),
        key="question",
    )
    go = st.button("Run graph", type="primary")
    if not go and "last_run" not in st.session_state:
        st.info("Ask a question. The graph will retrieve, grade evidence, then generate or refuse.")
        return
    if go:
        st.session_state["last_run"] = _run_query(question, ticker, section, as_of.strip())

    run = st.session_state["last_run"]
    result = run.answer
    state = run.state

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Decision", state.decision or "?")
    col_b.metric("Refused", "yes" if result.refused else "no")
    retrieve_ms = run.retrieve_ms or (state.trace.latency_ms if state.trace else 0.0)
    col_c.metric("Retrieve ms", f"{retrieve_ms:.1f}")
    col_d.metric("Graph ms", f"{run.latency_ms:.1f}")

    tok_a, tok_b, tok_c, tok_d = st.columns(4)
    tok_a.metric("Generate ms", f"{run.generate_ms:.1f}")
    tok_b.metric("Prompt toks", f"{run.usage.prompt_tokens}")
    tok_c.metric("Completion toks", f"{run.usage.completion_tokens}")
    tok_d.metric("Tokens", f"{run.usage.total_tokens} ({run.usage.source})")

    st.markdown("**Graph path:** `" + " → ".join(run.path) + "`")
    if result.refused:
        st.error(result.answer)
    else:
        st.success(result.answer)

    if result.citations:
        st.subheader("Citations")
        for cite in result.citations:
            st.markdown(f"- `{cite.format_line()}`")

    st.subheader("Evidence")
    if not state.chunks:
        st.warning("No chunks retrieved.")
        return
    for i, chunk in enumerate(state.chunks, start=1):
        meta = chunk.payload
        header = (
            f"[{i}] {meta.get('ticker')} {meta.get('form')} {meta.get('section')} "
            f"{meta.get('filing_date')}  score={chunk.score:.4f}"
        )
        with st.expander(header, expanded=(i == 1 and not result.refused)):
            rr = f"{chunk.rerank_score:.4f}" if chunk.rerank_score is not None else "—"
            st.markdown(
                f"chunk_id=`{chunk.chunk_id}` · dense_rank={chunk.dense_rank} · "
                f"sparse_rank={chunk.sparse_rank} · rerank={rr}"
            )
            st.write(chunk.text)


if __name__ == "__main__":
    main()
