"""Guardrails so interview docs stay non-empty."""

from pathlib import Path

from fintruth.config import REPO_ROOT


def test_design_decisions_has_logged_choices() -> None:
    text = (REPO_ROOT / "docs" / "design_decisions.md").read_text(encoding="utf-8")
    assert "D1." in text
    assert "Reciprocal Rank Fusion" in text
    assert "Refusal" in text or "refuse" in text.lower()


def test_failure_analysis_covers_demo_modes() -> None:
    text = (REPO_ROOT / "evals" / "failure_analysis.md").read_text(encoding="utf-8")
    assert "q015" in text
    assert "out of corpus" in text.lower() or "Out of corpus" in text
    assert "DEMO_CORPUS" in text
    assert Path(REPO_ROOT / "docs" / "architecture.md").stat().st_size > 200


def test_limitations_and_exceptional_work_are_filled() -> None:
    limits = (REPO_ROOT / "docs" / "limitations.md").read_text(encoding="utf-8")
    exceptional = (REPO_ROOT / "docs" / "exceptional_work.md").read_text(encoding="utf-8")
    assert "hash embedder" in limits.lower() or "hash-embedder" in limits.lower()
    assert "OUT" in limits
    assert "Truth-seeking" in exceptional or "refusal" in exceptional.lower()
    assert len(limits) > 400
    assert len(exceptional) > 400


def test_walkthrough_exists() -> None:
    text = (REPO_ROOT / "docs" / "walkthrough.md").read_text(encoding="utf-8")
    assert "10" in text and "minute" in text.lower()
    assert "refuse" in text.lower()
    assert "ingest-preflight" in text
    assert len(text) > 400


def test_changelog_describes_v010() -> None:
    text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "0.1.0" in text
    assert "q030" in text
