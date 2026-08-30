"""Offline tests for live-ingest preflight."""

from pathlib import Path

from fintruth.config import Settings
from fintruth.ingestion.preflight import (
    run_preflight,
    user_agent_is_placeholder,
)


def test_placeholder_user_agent_detected() -> None:
    assert user_agent_is_placeholder("FinTruthRAG contact@example.com")
    assert user_agent_is_placeholder("")
    assert user_agent_is_placeholder("short")
    assert not user_agent_is_placeholder("FinTruth RAG alice@university.edu")


def test_preflight_fails_on_example_agent(tmp_path: Path) -> None:
    settings = Settings(
        sec_user_agent="FinTruthRAG contact@example.com",
        data_raw_dir=tmp_path / "raw",
        data_processed_dir=tmp_path / "processed",
    )
    result = run_preflight(settings, check_network=False)
    assert result.ready is False
    names = {c.name: c.ok for c in result.checks}
    assert names["sec_user_agent"] is False
    assert names["data_dirs"] is True
    assert "not ready" in "\n".join(result.lines())


def test_preflight_passes_with_real_looking_agent(tmp_path: Path) -> None:
    settings = Settings(
        sec_user_agent="FinTruth RAG researcher@university.edu",
        data_raw_dir=tmp_path / "raw",
        data_processed_dir=tmp_path / "processed",
    )
    result = run_preflight(settings, check_network=False)
    ua = next(c for c in result.checks if c.name == "sec_user_agent")
    assert ua.ok is True
    dirs = next(c for c in result.checks if c.name == "data_dirs")
    assert dirs.ok is True
    assert (tmp_path / "raw").is_dir()
