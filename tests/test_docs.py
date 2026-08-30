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
