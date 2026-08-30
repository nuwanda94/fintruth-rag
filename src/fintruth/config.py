"""Runtime configuration loaded from environment / .env."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application settings. Values come from env vars or `.env`."""

    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    xai_api_key: str = ""
    xai_model: str = "grok-4"

    voyage_api_key: str = ""
    openai_api_key: str = ""
    embedding_model: str = "voyage-finance-2"

    cohere_api_key: str = ""

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "fintruth_chunks"

    sec_user_agent: str = "FinTruthRAG contact@example.com"
    catalog_db_path: Path = Field(default=REPO_ROOT / "data" / "catalog.db")
    data_raw_dir: Path = Field(default=REPO_ROOT / "data" / "raw")
    data_processed_dir: Path = Field(default=REPO_ROOT / "data" / "processed")

    log_level: str = "INFO"

    # Interview-max corpus: 8–12 large-caps, 3–5 years of 10-K + 10-Q.
    tickers: list[str] = Field(
        default_factory=lambda: [
            "AAPL",
            "MSFT",
            "GOOGL",
            "AMZN",
            "META",
            "NVDA",
            "JPM",
            "XOM",
            "UNH",
            "JNJ",
        ]
    )
    filing_forms: list[str] = Field(default_factory=lambda: ["10-K", "10-Q"])
    filing_years: int = 4

    # Chunking defaults (refined after first failure analysis).
    chunk_tokens: int = 512
    chunk_overlap_tokens: int = 64


def get_settings() -> Settings:
    """Return a fresh Settings instance (cheap; env is the source of truth)."""
    return Settings()
