.PHONY: help install lint test ingest index ask eval

help:
	@echo "FinTruth RAG"
	@echo "  make install   - sync deps with uv"
	@echo "  make lint      - ruff check"
	@echo "  make test      - pytest"
	@echo "  make ingest    - download + parse + chunk SEC filings"
	@echo "  make index     - embed catalog chunks into Qdrant"
	@echo "  make ask       - hybrid retrieve + grounded extractive answer"

install:
	uv sync --extra dev

lint:
	uv run ruff check src scripts tests

test:
	uv run pytest -q

ingest:
	uv run python scripts/ingest.py

index:
	uv run python scripts/index.py

ask:
	uv run python scripts/ask.py --demo "What competition risks does Apple disclose?"
