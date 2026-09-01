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

## 2026-08-31 — Session 2, Phase 01

**Done:**
- Stood up the macOS dev toolchain: installed `uv`, created the Python 3.12 venv
- Added `fastapi` + `uvicorn[standard]` as the first runtime dependencies, `httpx` as dev
- Built the target service: `app/target/{config,store,app,__main__}.py`
- Landed the structured JSON logging + correlation-ID foundation in `app/core/logging.py`
- Wrote unit + integration tests (24 passing); `ruff` and `mypy --strict` clean
- Verified live: `/pricing` at ~1.2ms baseline vs ~52.7ms with `SLOW_PRICING=1`, identical body

**Decided:**
- Regression switches live in `app/target/config.py` (the target's own knobs), not `app/core`,
  so the target does not import PulseForge tool configuration
- Error injection is deterministic (evenly spaced fraction), not random, so a replay is reproducible
- `/health` is never fault-injected: it is the liveness probe

**Open:**
- PR opened, awaiting Aadit's review and merge to `main`
- Phase 02 (capture) scope drafted, not started

**Learned:** port 8000 was already bound by an unrelated local process during the demo, which silently
served its own 404s; the readiness check now asserts the `/health` body, not merely a response. See FM-001.
