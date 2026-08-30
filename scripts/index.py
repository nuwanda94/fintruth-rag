"""CLI: embed catalog chunks and upsert into the vector store.

Usage:
    uv run python scripts/index.py
    uv run python scripts/index.py --limit 200
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fintruth.config import get_settings  # noqa: E402
from fintruth.indexing.embedder import build_embedder  # noqa: E402
from fintruth.indexing.qdrant_store import build_vector_store, index_payloads  # noqa: E402
from fintruth.ingestion.catalog import Catalog  # noqa: E402
from fintruth.logging import setup_logging  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Embed catalog chunks and upsert to Qdrant.")
    parser.add_argument("--limit", type=int, default=None, help="Max chunks to index")
    args = parser.parse_args()

    setup_logging()
    settings = get_settings()
    catalog = Catalog(settings=settings)
    payloads = list(catalog.iter_chunk_payloads())
    catalog.close()
    if args.limit is not None:
        payloads = payloads[: args.limit]
    if not payloads:
        print("index aborted: catalog has no chunks (run scripts/ingest.py first)")
        return 1

    embedder = build_embedder(settings)
    store = build_vector_store(settings)
    n = index_payloads(payloads, embedder=embedder, store=store, settings=settings)
    print(f"index done: upserted={n} collection={settings.qdrant_collection} model={embedder.model_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
