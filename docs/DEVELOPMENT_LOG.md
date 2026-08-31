# DEVELOPMENT_LOG

What was actually done, per session. Entries are written from what you tell me. Never invented.

## 2026-08-30 — Session 1, Phase 00

**Done:**
- Inspected the working directory: empty repo, two commits, remote already configured
- Answered bootstrap questions; chose recommended options for D1-D4
- Created `docs/` tree, phase stubs, and root documentation
- Recorded ADR-001 through ADR-006

**Decided:**
- ASGI middleware capture, content-addressed local files, BSL 1.1, noise-floor-calibrated thresholds,
  Python 3.12 + uv + ruff + mypy
- ADR-005 (WSL2 development environment) raised but left Proposed, pending a decision

- Wrote `pyproject.toml` and the empty package skeleton (`app/__init__.py`, `tests/` subdirs)
- Accepted ADR-005: development moves to WSL2 Ubuntu, repo on the Linux filesystem

**Open:**
- WSL2 migration not yet executed
- `uv sync` never run; `pyproject.toml` is unverified
- `PHASE_PROMPTS.md` at repo root: tracked or ignored, undecided

**Learned:** to be filled in by you.
