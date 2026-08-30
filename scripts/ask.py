"""CLI: retrieve hybrid evidence and print a grounded extractive answer.

Usage:
    uv run python scripts/ask.py "What competition risks does Apple disclose?"
    uv run python scripts/ask.py "iPhone revenue" --ticker AAPL --section mda
    uv run python scripts/ask.py "Apple competition" --demo --compare

Without a populated catalog this still demos the loop on a tiny in-memory
fixture so the retrieve → cite path is exercisable offline.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fintruth.config import get_settings  # noqa: E402
from fintruth.generation.chain import generate_answer  # noqa: E402
from fintruth.indexing.embedder import build_embedder  # noqa: E402
from fintruth.indexing.qdrant_store import InMemoryVectorStore, index_payloads  # noqa: E402
from fintruth.ingestion.catalog import Catalog  # noqa: E402
from fintruth.logging import setup_logging  # noqa: E402
from fintruth.retrieval.compare import compare_retrievers  # noqa: E402
from fintruth.retrieval.filters import RetrievalFilters  # noqa: E402
from fintruth.retrieval.hybrid import HybridRetriever  # noqa: E402

_DEMO_PAYLOADS = [
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
        "chunk_id": "XOM:demo:risk_factors:0",
        "text": "ExxonMobil commodity prices and refining margins remain volatile.",
        "ticker": "XOM",
        "form": "10-K",
        "filing_date": "2024-02-28",
        "section": "risk_factors",
    },
]


def _payloads_from_catalog(limit: int | None) -> list[dict]:
    settings = get_settings()
    catalog = Catalog(settings=settings)
    try:
        payloads = list(catalog.iter_chunk_payloads())
    except Exception:
        payloads = []
    finally:
        catalog.close()
    if limit is not None:
        payloads = payloads[:limit]
    return payloads


def build_retriever(payloads: list[dict]) -> HybridRetriever:
    settings = get_settings()
    embedder = build_embedder(settings)
    store = InMemoryVectorStore()
    index_payloads(payloads, embedder=embedder, store=store, settings=settings)
    retriever = HybridRetriever(store=store, embedder=embedder, settings=settings)
    retriever.add_sparse_corpus(payloads)
    return retriever


def main() -> int:
    parser = argparse.ArgumentParser(description="Hybrid retrieve + grounded extractive answer.")
    parser.add_argument("question", help="Natural-language research question")
    parser.add_argument("--ticker", action="append", dest="tickers", default=None)
    parser.add_argument("--section", action="append", dest="sections", default=None)
    parser.add_argument("--form", action="append", dest="forms", default=None)
    parser.add_argument("--as-of", dest="as_of", default=None, help="Point-in-time ISO date cutoff")
    parser.add_argument("--k", type=int, default=None, help="Final evidence count")
    parser.add_argument("--limit", type=int, default=None, help="Max catalog chunks to load")
    parser.add_argument("--demo", action="store_true", help="Force the built-in demo corpus")
    parser.add_argument("--no-rerank", action="store_true", help="Skip the lexical reranker")
    parser.add_argument("--compare", action="store_true", help="Print dense vs hybrid vs +rerank")
    parser.add_argument(
        "--extractive",
        action="store_true",
        help="Force the offline extractive path even if XAI_API_KEY is set",
    )
    args = parser.parse_args()

    setup_logging()
    payloads = [] if args.demo else _payloads_from_catalog(args.limit)
    source = "catalog"
    if not payloads:
        payloads = _DEMO_PAYLOADS
        source = "demo"

    retriever = build_retriever(payloads)
    filters = RetrievalFilters(
        tickers=args.tickers or [],
        forms=args.forms or [],
        sections=args.sections or [],
        as_of=args.as_of,
    )
    if args.compare:
        print("# Ablation  dense vs hybrid vs hybrid+rerank")
        for arm in compare_retrievers(retriever, args.question, filters=filters, final_k=args.k or 5):
            trace = arm.traces
            latency = f"{trace.latency_ms:.1f}ms" if trace else "?"
            print(f"  {arm.name:16} {latency:>8}  {arm.chunk_ids}")
        print()

    chunks = retriever.retrieve(
        args.question,
        filters=filters,
        final_k=args.k,
        rerank=not args.no_rerank,
    )
    result = generate_answer(args.question, chunks, use_llm=False if args.extractive else None)
    trace = retriever.last_trace

    print(
        f"# FinTruth ask  corpus={source}  n_chunks={len(payloads)}  "
        f"hits={len(chunks)}  rerank={not args.no_rerank}  mode={result.mode}  "
        f"latency_ms={trace.latency_ms:.1f}" if trace else ""
    )
    print(f"Q: {args.question}")
    print()
    print(result.answer)
    print()
    if result.citations:
        print("Citations:")
        for cite in result.citations:
            print(f"  {cite.format_line()}")
    print()
    print("Evidence:")
    for i, chunk in enumerate(chunks, start=1):
        meta = (
            f"{chunk.payload.get('ticker')} {chunk.payload.get('form')} "
            f"{chunk.payload.get('section')} {chunk.payload.get('filing_date')}"
        )
        rr = f"{chunk.rerank_score:.4f}" if chunk.rerank_score is not None else "-"
        print(
            f"  [{i}] score={chunk.score:.4f} rerank={rr} "
            f"dense={chunk.dense_rank} sparse={chunk.sparse_rank} {meta}"
        )
        preview = chunk.text.replace("\n", " ")[:180]
        print(f"      {preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
