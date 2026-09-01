# Phase 01 — TARGET SERVICE

> **Status: complete (pending PR merge).** Built 2026-08-31.

## Goal

Build a small FastAPI service with switchable, deliberate regressions (`SLOW_PRICING`, `N_PLUS_ONE`, `ERROR_RATE`) so every later phase has ground truth to verify against.

## Why this exists

The gate, the replay engine, and the comparison engine all need something to run against whose
behaviour is known in advance. This service is that ground truth: a *subject* under test, not part of
the PulseForge tool (ARCHITECTURE.md). Each switch reproduces a real regression class — a slow path,
an N+1 query, an elevated error rate — while leaving the business result unchanged, which is exactly
the blind spot a correctness test suite has and the gate is built to cover.

## Design

- **`app/target/config.py`** — `TargetConfig`, a frozen dataclass reading the three switches from the
  environment, off by default (the baseline). Regression config is the target's own concern, so it
  lives here rather than in `app/core`.
- **`app/target/store.py`** — an in-memory stand-in for a database. Each simulated query costs a small
  fixed latency, so the N+1 pattern (one query per order vs one batched query) shows up as measurable
  latency. Dataset is small and fixed for reproducibility.
- **`app/target/app.py`** — the FastAPI app factory and endpoints (`/health`, `/pricing/{sku}`,
  `/orders`), plus `DeterministicErrorInjector` and correlation-ID middleware. Error injection is
  deterministic (evenly spaced), never random, so a replay is reproducible; `/health` is never failed.
- **`app/core/logging.py`** — structured JSON logging with a per-request correlation ID
  (OBSERVABILITY.md), landed now because it cannot be retrofitted.

## Relevant decisions

- ADR-001 — the target is a FastAPI/ASGI app, matching the capture mechanism Phase 02 will use.
- ADR-006 — Python 3.12, `uv`, `ruff`, `mypy --strict`.

## Files in scope

- `app/core/__init__.py`, `app/core/logging.py`
- `app/target/__init__.py`, `app/target/config.py`, `app/target/store.py`, `app/target/app.py`,
  `app/target/__main__.py`
- `tests/unit/test_target_config.py`, `tests/integration/test_target_service.py`
- `pyproject.toml` (added `fastapi`, `uvicorn[standard]`, dev `httpx`), `uv.lock`

## Exit criteria

- [x] Feature works, with pasted output proving it (`/pricing` ~1.2ms baseline vs ~52.7ms slow)
- [x] Unit tests pass and cover failure paths, not only the happy path
- [x] Integration test exists where this phase crosses a component boundary (HTTP/ASGI)
- [x] `ruff check`, `ruff format --check`, and `mypy --strict app/` all clean
- [x] One deliberate failure injected, observed, and recorded in `FAILURE_MODES.md` (FM-001)
- [x] Docs updated per the trigger table
- [ ] Any measured numbers in `BENCHMARKS.md` with reproduction steps — deferred; the timing above is
      illustrative, not a benchmark, and formal numbers wait for the replay/compare engines (Phases 04–05)
- [x] Commit commands printed and run
- [x] Next phase doc updated with its scope list
