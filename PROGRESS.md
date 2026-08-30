# FinTruth RAG — Progress Log

This file is the running log of automated and manual iterations.  
Every run must append a new entry at the top (most recent first).

---

## Iteration 0 — Bootstrap (2026-08-30)

**Completed**
- Created GitHub repository: https://github.com/nuwanda94/fintruth-rag
- Added README.md with project overview, scope, stack, and structure
- Added ROADMAP.md (full interview-max week-by-week plan — single source of truth)
- Initialized this PROGRESS.md

**Current Status**
- Week 1, Day 1 not yet started
- Repo exists and is empty of code (structure and docs only)

**Next Iteration Should Pick Up**
1. Create full folder structure under `src/`, `scripts/`, `data/`, `evals/`, `docs/`, `tests/`, `notebooks/`
2. Add `pyproject.toml` with core dependencies (uv-compatible)
3. Add `.env.example`, `Makefile`, basic `src/fintruth/config.py`
4. Implement skeleton for ingestion (downloader.py, parser.py, chunker.py)
5. Commit as: `chore: scaffold project structure and config`

**Blockers / Notes**
- None. Ready for first code iteration.
- Automation should follow ROADMAP.md strictly and always update this file.
