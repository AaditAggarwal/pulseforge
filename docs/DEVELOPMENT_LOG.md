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
- `app/target/`: config, SQLite schema and deterministic seed, connection pool, pricing module,
  fault injection, app factory, five endpoints
- Four runtime regression switches wired and proven to change behaviour: `SLOW_PRICING_MS`,
  `N_PLUS_ONE`, `ERROR_RATE`, `TIMEOUT_RATE`
- 113 tests passing, 99% branch coverage on `app/target`
- `scripts/phase01_evidence.py`, which reproduces every number in `BENCHMARKS.md` B-01 and B-02
- Recorded FM-001 with a regression test

**Decided:**
- `SLOW_PRICING` became `SLOW_PRICING_MS` (integer ms, 0 = off) so the fault has a magnitude to
  sweep, not just an on/off state. `.env.example` and the V0 definition updated to match.
- Pricing lives in its own module called by two routes, so the fault's blast radius spans endpoints
  of different shapes rather than one route
- One uniform RNG draw picks between error, timeout and neither, so configured rates are observed
  rates exactly; `ERROR_RATE + TIMEOUT_RATE > 1.0` is now a startup error
- `order_items(order_id)` stays indexed so the injected N+1 is realistic rather than a strawman
- Raw ASGI middleware rather than `BaseHTTPMiddleware`, to keep injection-layer overhead out of the
  numbers the gate compares
- `aiosqlite` over an in-memory dict, so the N+1 costs real I/O
- Connection pool rather than one shared connection, so the N+1 is not measured as queueing
- `httpx2` replaced `httpx` as the test client dependency (starlette 1.6 deprecation)

**Open:**
- Q7 raised: per-request determinism of injected faults under concurrency. Resolve by Phase 04.
- `POST /orders` prices once per line item, so injected pricing latency scales with payload size.
  Deliberate, flagged for Phase 05.
- `SLOW_PRICING_MS` models I/O wait only. A CPU-bound regression would be a different switch.

**Learned:** to be filled in by you.
