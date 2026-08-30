"""Offline tests for the Week 1 eval harness."""

from fintruth.eval.dataset import load_questions
from fintruth.eval.metrics import score_item, summarize
from fintruth.eval.runner import DEMO_CORPUS, build_retriever, evaluate_question, run_eval
from fintruth.generation.chain import GroundedAnswer
from fintruth.eval.dataset import EvalQuestion


def test_questions_jsonl_has_interview_floor() -> None:
    items = load_questions()
    assert len(items) >= 30
    assert any(q.expect_refuse for q in items)
    assert any(q.category == "out_of_corpus" for q in items)
    assert any(q.category == "multi_ticker" for q in items)
    ids = [q.id for q in items]
    assert len(ids) == len(set(ids))


def test_score_item_rewards_correct_refusal() -> None:
    q = EvalQuestion(
        id="x",
        question="Tesla deliveries?",
        tickers=["TSLA"],
        expect_refuse=True,
        must_cite=False,
    )
    result = GroundedAnswer(
        question=q.question,
        answer="REFUSAL: out of corpus",
        refused=True,
        refusal_reason="out of corpus",
    )
    score = score_item(q, result)
    assert score.refusal_ok
    assert score.composite == 1.0


def test_demo_eval_runs_and_refuses_out_of_corpus() -> None:
    questions = load_questions()
    run = run_eval(questions=questions, demo=True, write=False)
    assert run.corpus == "demo"
    assert run.summary["n"] == float(len(questions))
    assert run.summary["composite"] > 0.5
    by_id = {row["id"]: row for row in run.items}
    assert by_id["q015"]["refused"] is True
    assert by_id["q029"]["refused"] is True
    assert by_id["q001"]["refused"] is False
    assert by_id["q001"]["citations"]
    assert "Sources:" in by_id["q001"]["answer"]


def test_evaluate_question_on_demo_retriever() -> None:
    retriever = build_retriever(DEMO_CORPUS)
    q = EvalQuestion(
        id="q001",
        question="What competition risks does Apple disclose in its 10-K?",
        tickers=["AAPL"],
        forms=["10-K"],
        sections=["risk_factors"],
        keywords=["competition"],
    )
    score, row = evaluate_question(q, retriever)
    assert score.keyword_ok
    assert row["n_hits"] >= 1
    assert summarize([score])["n"] == 1.0
