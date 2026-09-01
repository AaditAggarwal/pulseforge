# PROJECT_CONTEXT

> Single source of truth. Read this in full at the start of every session, before anything else.
> If this file and the code disagree, **the code is truth and this file is a bug.** Say so immediately and fix it.

## What PulseForge is

A change-aware performance regression gate for API services.

Tests verify correctness, not behaviour under load. A change can pass every test and still double p95
latency, introduce an N+1 query, or exhaust a connection pool. PulseForge records real API traffic,
sanitizes it, and replays a byte-identical workload against the currently-deployed version (baseline)
and the proposed version (candidate). It compares latency distributions and error rates and emits a
machine-readable PASS/BLOCK verdict that CI enforces.

The intended differentiator, **not yet built**: the workload is weighted toward the blast radius of the
diff, using a coverage map recorded during capture, with an LLM assisting where static analysis goes
blind (new endpoints with no traffic history, config/dependency changes, semantic risk patterns).

## Status

| | |
|---|---|
| Current phase | **02 — Capture** (not started) |
| Phases complete | 00, 01 |
| Lines of application code | 1022 in `app/`, of which ~700 are the Phase 01 target service |
| Tests | 113 passing; 99% branch coverage on `app/target` |
| Measured numbers | Phase 01 target service only. See `BENCHMARKS.md` B-01 to B-03. |
| Last updated | 2026-08-31 |

**Nothing in the "What PulseForge is" section above is implemented yet.** The target service is the
subject PulseForge will be pointed at, not PulseForge itself. Treat every capability as unbuilt until
this file's "What works" table says otherwise.

## What works

| Component | Status | Evidence |
|---|---|---|
| `app/core` — errors, JSON logging, correlation IDs | Built | `tests/unit/test_logging.py` |
| `app/target` — 5-endpoint FastAPI service, SQLite-backed | Built | `BENCHMARKS.md` B-01 |
| `app/target` — 4 runtime regression switches | Built | `BENCHMARKS.md` B-02; `tests/integration/test_target_faults.py` |

The switches are the ground truth for everything downstream: `SLOW_PRICING_MS` degrades two routes
through a shared module, `N_PLUS_ONE` degrades one route by 4.4x while returning byte-identical
responses, and `ERROR_RATE`/`TIMEOUT_RATE` deliver the configured rates within sampling error.

## What does not work

Capture, coverage mapping, replay, comparison, the gate, the planner — every part of PulseForge
itself. Only the thing it will be tested against exists. See the phase list below.

## Stack

| Concern | Choice | ADR |
|---|---|---|
| Language | Python 3.12 (`>=3.12,<3.13`) | ADR-006 |
| Dependency management | `uv`, lockfile committed | ADR-006 |
| Lint + format | `ruff` | ADR-006 |
| Type checking | `mypy --strict` on `app/` | ADR-006 |
| Test | `pytest`, `pytest-asyncio`, `pytest-cov`, `hypothesis` | — |
| Web framework | FastAPI (target service and capture middleware) | ADR-001 |
| Traffic capture | ASGI middleware, in-process | ADR-001 |
| Artifact storage | content-addressed files on local FS | ADR-002 |
| License | Business Source License 1.1 → Apache 2.0 on 2030-08-30 | ADR-003 |
| Regression criterion | delta vs measured noise floor | ADR-004 |
| Dev environment | WSL2 Ubuntu, repo on the Linux filesystem | ADR-005 |
| LLM provider | OpenRouter (Phase 07; ~$4 credit available) | — |

## Environment as actually observed (2026-08-30)

- Host: Windows 11 Home 10.0.26200. **Development happens inside WSL2 Ubuntu** (ADR-005), repo at
  `~/projects/pulseforge` on the Linux filesystem. WSL2 RAM is capped at half the host — record this
  alongside every benchmark, since it bounds replay concurrency.
- Editing via VS Code with the WSL remote extension. Never through `\wsl.localhost\`.
- Windows-side toolchain observed before the move: Python 3.12.10, uv 0.11.2, Docker 29.5.2,
  gh 2.96.0, Node 24.19.0. WSL-side versions: NOT YET VERIFIED.
- `make` deliberately not installed on Windows; `uv run` is the task interface, `Makefile` is a
  wrapper for WSL2 and CI. `terraform` and `aws` CLI not installed; not needed before Phase 11.
- AWS account created ~2026-08-28, upgraded to Paid Plan. Credit balance NOT YET VERIFIED — check Billing console before Phase 11.

## Phase order

```
00  Foundation, repo scaffolding, tooling, CI skeleton          <- current
01  Target service + deliberate regression switches
02  Traffic capture + sanitization pipeline
03  Coverage mapping: route -> executed code paths
04  Replay engine, async, local, correct before fast
05  Comparison engine + statistics + noise floor
06  Regression gate: thresholds, verdict artifact, exit codes    <- V0 ends here; sellable slice
07  AI workload planner: diff -> frozen workload plan
08  Planner evaluation vs random sampling at equal budget
09  Queue + distributed workers, local first
10  Docker, Compose, GitHub Actions, gate running in real CI
11  AWS + Terraform
12  Observability: logs, metrics, traces
13  Failure injection, benchmarks, demo, launch readiness
```

The gate is built before distribution. The gate is the product; workers are an optimization.
Reordering requires an ADR.

## V0 — the thinnest sellable slice

Phases 00-06. One command against the Phase 01 target service produces a signed PASS/BLOCK verdict
on disk with a nonzero exit code on BLOCK, proven by flipping `SLOW_PRICING_MS`.

Deliberately excluded from V0: AI planner, coverage map, queue/workers, AWS, observability stack,
PR comment rendering. Each is leverage on the gate, and meaningless before the gate is trustworthy.

## Where to look next

- Component boundaries and data flow: `ARCHITECTURE.md`
- Why anything is the way it is: `DECISIONS.md`
- What is still undecided: `OPEN_QUESTIONS.md`
- What this phase requires: `PHASES/PHASE_02_CAPTURE.md`
- What was built last, and why it is shaped that way: `PHASES/PHASE_01_TARGET_SERVICE.md`
