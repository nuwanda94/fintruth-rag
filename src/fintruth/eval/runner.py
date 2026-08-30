"""Offline-first eval loop: retrieve → generate → score → JSONL results."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fintruth.config import REPO_ROOT, Settings, get_settings
from fintruth.eval.dataset import EvalQuestion, load_questions
from fintruth.eval.metrics import ItemScore, score_item, summarize
from fintruth.generation.chain import generate_answer
from fintruth.indexing.embedder import build_embedder
from fintruth.indexing.qdrant_store import InMemoryVectorStore, index_payloads
from fintruth.ingestion.catalog import Catalog
from fintruth.retrieval.filters import RetrievalFilters
from fintruth.retrieval.hybrid import HybridRetriever

DEFAULT_RESULTS_DIR = REPO_ROOT / "evals" / "results"

# Compact fixture so the harness runs before live SEC ingest.
DEMO_CORPUS: list[dict[str, Any]] = [
    {
        "chunk_id": "AAPL:demo:risk_factors:0",
        "text": "Apple faces intense competition in smartphones, wearables, and services.",
        "ticker": "AAPL",
        "form": "10-K",
        "filing_date": "2024-11-01",
        "section": "risk_factors",
    },
    {
        "chunk_id": "AAPL:demo:mda:0",
        "text": "iPhone revenue increased year over year driven by services mix.",
        "ticker": "AAPL",
        "form": "10-K",
        "filing_date": "2024-11-01",
        "section": "mda",
    },
    {
        "chunk_id": "MSFT:demo:risk_factors:0",
        "text": "Microsoft faces competition in cloud infrastructure and productivity software.",
        "ticker": "MSFT",
        "form": "10-K",
        "filing_date": "2024-07-30",
        "section": "risk_factors",
    },
    {
        "chunk_id": "MSFT:demo:mda:0",
        "text": "Azure revenue continued to grow as customers expanded cloud workloads.",
        "ticker": "MSFT",
        "form": "10-K",
        "filing_date": "2024-07-30",
        "section": "mda",
    },
    {
        "chunk_id": "GOOGL:demo:risk_factors:0",
        "text": "Alphabet advertising revenues remain sensitive to competition and regulation.",
        "ticker": "GOOGL",
        "form": "10-K",
        "filing_date": "2024-01-31",
        "section": "risk_factors",
    },
    {
        "chunk_id": "AMZN:demo:risk_factors:0",
        "text": "Amazon fulfillment network capacity and logistics costs are material risks.",
        "ticker": "AMZN",
        "form": "10-K",
        "filing_date": "2024-02-02",
        "section": "risk_factors",
    },
    {
        "chunk_id": "META:demo:risk_factors:0",
        "text": "Meta faces regulatory scrutiny around content moderation and privacy.",
        "ticker": "META",
        "form": "10-K",
        "filing_date": "2024-02-01",
        "section": "risk_factors",
    },
    {
        "chunk_id": "NVDA:demo:risk_factors:0",
        "text": "NVIDIA supply chain concentration and manufacturing capacity are key risks.",
        "ticker": "NVDA",
        "form": "10-K",
        "filing_date": "2024-02-21",
        "section": "risk_factors",
    },
    {
        "chunk_id": "NVDA:demo:mda:0",
        "text": "Data center revenue grew faster than gaming as AI training demand rose.",
        "ticker": "NVDA",
        "form": "10-K",
        "filing_date": "2024-02-21",
        "section": "mda",
    },
    {
        "chunk_id": "JPM:demo:risk_factors:0",
        "text": "JPMorgan credit losses and interest-rate movements can pressure earnings.",
        "ticker": "JPM",
        "form": "10-K",
        "filing_date": "2024-02-16",
        "section": "risk_factors",
    },
    {
        "chunk_id": "XOM:demo:risk_factors:0",
        "text": "ExxonMobil commodity prices and climate or energy-transition policy remain volatile risks.",
        "ticker": "XOM",
        "form": "10-K",
        "filing_date": "2024-02-28",
        "section": "risk_factors",
    },
    {
        "chunk_id": "UNH:demo:mda:0",
        "text": "UnitedHealth medical cost trends increased, pressuring insurance margins.",
        "ticker": "UNH",
        "form": "10-K",
        "filing_date": "2024-02-28",
        "section": "mda",
    },
    {
        "chunk_id": "JNJ:demo:risk_factors:0",
        "text": "Johnson & Johnson product-liability and litigation matters remain outstanding risks.",
        "ticker": "JNJ",
        "form": "10-K",
        "filing_date": "2024-02-16",
        "section": "risk_factors",
    },
]


@dataclass(slots=True)
class EvalRunResult:
    """Full run payload written under evals/results/."""

    corpus: str
    n_chunks: int
    summary: dict[str, float]
    items: list[dict[str, Any]] = field(default_factory=list)
    started_at: str = ""


def _payloads_from_catalog(settings: Settings) -> list[dict[str, Any]]:
    catalog = Catalog(settings=settings)
    try:
        return list(catalog.iter_chunk_payloads())
    except Exception:
        return []
    finally:
        catalog.close()


def build_retriever(payloads: list[dict[str, Any]], settings: Settings | None = None) -> HybridRetriever:
    settings = settings or get_settings()
    embedder = build_embedder(settings)
    store = InMemoryVectorStore()
    index_payloads(payloads, embedder=embedder, store=store, settings=settings)
    retriever = HybridRetriever(store=store, embedder=embedder, settings=settings)
    retriever.add_sparse_corpus(payloads)
    return retriever


def evaluate_question(
    question: EvalQuestion,
    retriever: HybridRetriever,
    *,
    final_k: int | None = None,
) -> tuple[ItemScore, dict[str, Any]]:
    filters = RetrievalFilters(
        tickers=question.tickers,
        forms=question.forms,
        sections=question.sections,
    )
    chunks = retriever.retrieve(question.question, filters=filters, final_k=final_k)
    # Eval stays extractive so scores are deterministic even if XAI_API_KEY is set.
    result = generate_answer(question.question, chunks, use_llm=False)
    score = score_item(question, result)
    row = {
        "id": question.id,
        "question": question.question,
        "category": question.category,
        "difficulty": question.difficulty,
        "expect_refuse": question.expect_refuse,
        "refused": result.refused,
        "refusal_reason": result.refusal_reason,
        "mode": result.mode,
        "answer": result.answer,
        "citations": [asdict(c) for c in result.citations],
        "n_hits": len(chunks),
        "top_score": chunks[0].score if chunks else 0.0,
        "score": asdict(score),
    }
    return score, row


def run_eval(
    *,
    questions: list[EvalQuestion] | None = None,
    demo: bool = False,
    settings: Settings | None = None,
    results_dir: Path | None = None,
    write: bool = True,
) -> EvalRunResult:
    """Execute the seeded set against catalog chunks or the demo fixture."""
    settings = settings or get_settings()
    questions = questions if questions is not None else load_questions()
    payloads = [] if demo else _payloads_from_catalog(settings)
    corpus = "catalog"
    if not payloads:
        payloads = DEMO_CORPUS
        corpus = "demo"

    retriever = build_retriever(payloads, settings=settings)
    scores: list[ItemScore] = []
    rows: list[dict[str, Any]] = []
    for item in questions:
        score, row = evaluate_question(item, retriever)
        scores.append(score)
        rows.append(row)

    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    run = EvalRunResult(
        corpus=corpus,
        n_chunks=len(payloads),
        summary=summarize(scores),
        items=rows,
        started_at=started,
    )
    if write:
        out_dir = results_dir or DEFAULT_RESULTS_DIR
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = out_dir / f"run_{corpus}_{stamp}.json"
        path.write_text(json.dumps(asdict(run), indent=2), encoding="utf-8")
        latest = out_dir / "latest.json"
        latest.write_text(json.dumps(asdict(run), indent=2), encoding="utf-8")
    return run
