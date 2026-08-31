# ARCHITECTURE

> Components, data flow, interfaces, and why the boundaries sit where they do.
> Status of every component below: **designed, not built.** Phase 00 is scaffolding only.

## Data flow (V0, phases 00-06)

```
                    CAPTURE TIME (developer machine or staging)
  client ──HTTP──> [ target service ]
                        │
                   ASGI middleware (ADR-001)
                        │  sanitize BEFORE any write (SECURITY.md)
                        ▼
                   corpus/<hash>.jsonl        content-addressed (ADR-002)

                    GATE TIME (CI)
  corpus ──> [ workload planner ] ──> plan.json  (frozen, hashed, written once)
                                          │
                        ┌─────────────────┴─────────────────┐
                        ▼                                   ▼
                 [ replay engine ]                   [ replay engine ]
                   vs BASELINE                         vs CANDIDATE
                        │                                   │
                  baseline.jsonl                     candidate.jsonl
                        └─────────────────┬─────────────────┘
                                          ▼
                              [ comparison engine ]   p50/p95/p99, error rate,
                                          │           noise floor (ADR-004)
                                          ▼
                                   [ regression gate ]
                                          ▼
                                    verdict.json  + exit code 0 | 1
```

In V0 the "workload planner" is a deterministic sampler with a fixed seed. Phase 07 replaces its
internals with the diff-aware, LLM-assisted planner. **The interface does not change** — that is the
entire point of building the gate first.

## Components

| Package | Owns | Must not know about |
|---|---|---|
| `app/core` | errors, structured logging, correlation IDs, config, hashing | everything else — it imports nothing from `app/` |
| `app/target` | the Phase 01 service under test, with regression switches | PulseForge itself; it is a *subject*, not a part of the tool |
| `app/capture` | ASGI middleware, sanitization, corpus writing | replay, comparison, verdicts |
| `app/storage` | reading/writing artifacts, content addressing, schema versions | what any artifact *means* |
| `app/replay` | executing a frozen plan against a base URL, timing each request | how the plan was chosen, what the results mean |
| `app/compare` | statistics, noise floor, distribution comparison — pure functions | I/O, HTTP, filesystem |
| `app/gate` | thresholds, verdict construction, exit codes | statistics internals |
| `app/planner` | diff -> workload plan (Phase 07) | how the plan is executed |

## Why the boundaries sit here

**`compare` is pure functions with no I/O.** Statistics is where subtle bugs hide and where the
interview questions land. Pure functions are testable with property-based tests and no fixtures. If
`compare` ever imports `httpx` or `pathlib`, that is a design regression.

**`replay` does not know how the plan was chosen.** This is what makes R7 enforceable: replay reads a
frozen, hashed plan file and executes it. It has no branch that could differ between baseline and
candidate, because it has no knowledge that "baseline" and "candidate" are different things — it
receives a base URL and a plan.

**`storage` is a seam, not an abstraction layer.** One implementation (local FS) exists today. It
exists as a separate package solely because Phase 11 swaps it for S3, and that swap must not touch
`capture`, `replay`, or `gate`. Per §8, no second abstraction until there is a second user.

**`target` lives in this repo but is not part of the product.** It is ground truth for testing. It
ships in the repo so every phase has something verifiable to run against; it would not ship to a
customer.

**`capture` sanitizes before writing.** Sanitization is not a stage in a pipeline that could be
reordered — it is inside the write path. Raw traffic never reaches a filesystem. See `SECURITY.md`.

## Interfaces (shapes, not yet code)

Every artifact crossing a boundary is a Pydantic model carrying `schema_version` from day one.

- `CapturedRequest` — sanitized request/response pair plus timing and route metadata
- `WorkloadPlan` — ordered list of plan entries, a seed, a concurrency setting, and `plan_id` (content hash)
- `ReplayResult` — per-request outcome: status, latency ns, error class; plus run metadata
- `ComparisonReport` — per-endpoint and aggregate distribution statistics, including the noise floor
- `Verdict` — PASS/BLOCK, the rule that fired, the numbers behind it, and the inputs' hashes

Concrete schemas are defined in the phase that first needs them, not before.

## Not yet designed

Coverage mapping (03), planner prompt/schema (07), queue topology (09), AWS topology (11),
trace propagation (12). Each is designed in its own phase, and this file is updated only if a
boundary above actually moves.
