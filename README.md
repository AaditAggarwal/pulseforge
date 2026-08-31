# PulseForge

**A change-aware performance regression gate for API services.**

> **Status: Phase 00 of 13. No application code exists yet.** Everything below the next heading
> describes the intended system. Nothing in it is implemented. See
> [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md) for what is actually true today.

## The problem

Tests verify correctness, not behaviour under realistic load. A change can pass every test in CI and
still double p95 latency, introduce an N+1 query, or exhaust a connection pool. Teams find out in
production.

## The intended approach

PulseForge records real API traffic, sanitizes it before it touches disk, and replays a byte-identical
workload against the currently-deployed version (baseline) and the proposed version (candidate). It
compares latency distributions and error rates against a measured noise floor, and emits a
machine-readable PASS / BLOCK / INCONCLUSIVE verdict that CI enforces.

The intended differentiator: the replayed workload is weighted toward the blast radius of the diff,
using a coverage map recorded during capture, with an LLM assisting only where static analysis goes
blind. A 200ms regression in checkout should not be diluted across 9,000 unrelated `/health` requests.

The LLM shapes the workload. It never makes the gate decision — threshold comparison is deterministic
arithmetic, and a model outage falls back to full-corpus replay.

## Documentation

| | |
|---|---|
| What is true right now | [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md) |
| Components and boundaries | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| Why anything is the way it is | [`docs/DECISIONS.md`](docs/DECISIONS.md) |
| Still undecided | [`docs/OPEN_QUESTIONS.md`](docs/OPEN_QUESTIONS.md) |
| Sanitization and threat model | [`docs/SECURITY.md`](docs/SECURITY.md) |
| Measured numbers | [`docs/BENCHMARKS.md`](docs/BENCHMARKS.md) — currently empty, by design |

## No metrics here yet

This README will not carry a performance claim until a number exists in `BENCHMARKS.md` that came from
a run that actually happened, with reproduction steps beside it.

## License

Business Source License 1.1. Free for non-production use; converts to Apache 2.0 on 2030-08-30.
Rationale in ADR-003. See [`LICENSE`](LICENSE).
