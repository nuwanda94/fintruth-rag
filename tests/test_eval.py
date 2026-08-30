"""Offline tests for the eval harness, numerical checks, and ablation."""

import json
from pathlib import Path

from fintruth.config import REPO_ROOT
from fintruth.eval.ablation import run_retrieval_ablation
from fintruth.eval.dataset import EvalQuestion, load_questions
from fintruth.eval.metrics import extract_numbers, score_item, summarize
from fintruth.eval.runner import DEMO_CORPUS, build_retriever, evaluate_question, run_eval
from fintruth.generation.chain import Citation, GroundedAnswer
from fintruth.retrieval.hybrid import RetrievedChunk


def _chunk(chunk_id: str, text: str, ticker: str, **payload: str) -> RetrievedChunk:
    data = {"ticker": ticker, "form": "10-K", "section": "mda", "filing_date": "2024-11-01"}
    data.update(payload)
    return RetrievedChunk(
        chunk_id=chunk_id,
        text=text,
        score=0.2,
        dense_rank=1,
        sparse_rank=None,
        payload=data,
    )


def test_questions_jsonl_has_interview_floor() -> None:
    items = load_questions()
    assert len(items) >= 30
    assert any(q.expect_refuse for q in items)
    assert any(q.category == "out_of_corpus" for q in items)
    assert any(q.category == "multi_ticker" for q in items)
    assert any(q.expected_numbers for q in items)
    ids = [q.id for q in items]
    assert len(ids) == len(set(ids))


def test_extract_numbers_normalizes_currency() -> None:
    assert "201" in extract_numbers("iPhone net sales were $201 billion")
    assert extract_numbers("no figures here") == set()


def test_score_item_rewards_correct_refusal() -> None:
    q = EvalQuestion(
        id="x",
        question="Tesla deliveries?",
        tickers=["TSLA"],
        expect_refuse=True,
        must_cite=False,
        category="out_of_corpus",
    )
    result = GroundedAnswer(
        question=q.question,
        answer="REFUSAL: out of corpus",
        refused=True,
        refusal_reason="out of corpus",
    )
    score = score_item(q, result)
    assert score.refusal_ok
    assert score.numerical_ok
    assert score.citation_support_ok
    assert score.composite == 1.0


def test_numerical_score_requires_gold_in_answer_and_evidence() -> None:
    q = EvalQuestion(
        id="num",
        question="What were iPhone net sales?",
        tickers=["AAPL"],
        expected_numbers=["201"],
    )
    chunk = _chunk("AAPL:demo:mda:0", "iPhone net sales were $201 billion for fiscal 2024.", "AAPL")
    good = GroundedAnswer(
        question=q.question,
        answer="iPhone net sales were $201 billion [1]",
        refused=False,
        refusal_reason=None,
        citations=[Citation(1, chunk.chunk_id, "AAPL", "10-K", "mda", "2024-11-01")],
        chunks=[chunk],
    )
    assert score_item(q, good).numerical_ok
    bad = GroundedAnswer(
        question=q.question,
        answer="iPhone net sales were strong [1]",
        refused=False,
        refusal_reason=None,
        citations=[Citation(1, chunk.chunk_id, "AAPL", "10-K", "mda", "2024-11-01")],
        chunks=[chunk],
    )
    assert not score_item(q, bad).numerical_ok


def test_citation_support_rejects_foreign_ticker() -> None:
    q = EvalQuestion(id="c", question="Apple risks?", tickers=["AAPL"], must_cite=True)
    chunk = _chunk("MSFT:x", "Microsoft faces competition", "MSFT", section="risk_factors")
    result = GroundedAnswer(
        question=q.question,
        answer="competition [1]",
        refused=False,
        refusal_reason=None,
        citations=[Citation(1, chunk.chunk_id, "MSFT", "10-K", "risk_factors", "2024-01-01")],
        chunks=[chunk],
    )
    assert not score_item(q, result).citation_support_ok


def test_demo_eval_runs_and_refuses_out_of_corpus() -> None:
    questions = load_questions()
    run = run_eval(questions=questions, demo=True, write=False, with_ablation=False)
    assert run.corpus == "demo"
    assert run.summary["n"] == float(len(questions))
    assert run.summary["composite"] > 0.5
    assert "numerical_accuracy" in run.summary
    assert "citation_support" in run.summary
    by_id = {row["id"]: row for row in run.items}
    assert by_id["q015"]["refused"] is True
    assert by_id["q029"]["refused"] is True
    assert by_id["q030"]["refused"] is True
    assert "2012" in (by_id["q030"]["refusal_reason"] or "")
    assert by_id["q001"]["refused"] is False
    assert by_id["q001"]["citations"]
    assert "Sources:" in by_id["q001"]["answer"]
    assert by_id["q002"]["score"]["numerical_ok"] is True


def test_run_eval_writes_latest_json(tmp_path: Path) -> None:
    questions = load_questions()[:3]
    run = run_eval(
        questions=questions,
        demo=True,
        write=True,
        results_dir=tmp_path,
        with_ablation=True,
    )
    latest = tmp_path / "latest.json"
    assert latest.exists()
    assert run.ablation is not None
    assert run.ablation["n"] == 3


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


def test_retrieval_ablation_has_three_arms() -> None:
    retriever = build_retriever(DEMO_CORPUS)
    q = EvalQuestion(
        id="q001",
        question="What competition risks does Apple disclose in its 10-K?",
        tickers=["AAPL"],
        forms=["10-K"],
        sections=["risk_factors"],
        keywords=["competition"],
    )
    summary = run_retrieval_ablation([q], retriever)
    assert set(summary.arms) == {"dense", "hybrid", "hybrid+rerank"}
    assert summary.arms["hybrid"] == 1.0


def test_checked_in_latest_results_snapshot() -> None:
    path = REPO_ROOT / "evals" / "results" / "latest.json"
    assert path.exists(), "commit evals/results/latest.json from make eval --demo"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["corpus"] == "demo"
    assert payload["summary"]["n"] >= 30
    assert payload["summary"]["composite"] > 0.5
    assert "numerical_accuracy" in payload["summary"]
    assert payload.get("ablation", {}).get("arms")
