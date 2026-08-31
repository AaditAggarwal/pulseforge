# TESTING

## Layers

| Layer | Location | Covers | Cost |
|---|---|---|---|
| Unit | `tests/unit` | pure logic: sanitization rules, statistics, threshold arithmetic, plan hashing | milliseconds |
| Property | `tests/property` | the sanitizer, via `hypothesis` | seconds |
| Integration | `tests/integration` | boundaries: capture to storage, queue to worker, planner to schema validation | seconds |
| End-to-end | `tests/e2e` | the full gate against the Phase 01 target service | tens of seconds |

## Deliberate choices

**Property-based tests only for the sanitizer.** It is the one component where a miss is a security
incident rather than a bug, and example-based tests will not find the header nobody thought of.
Applying `hypothesis` everywhere would buy little and cost real time.

**Golden-file tests for verdict artifacts.** The verdict is the product output. Its shape changing
silently is a breaking change for every consumer, so the shape is pinned to a committed file.

**Contract tests for LLM output run against a recorded fixture, never a live API.** Tests must not
require network access, cost money, or fail because a third party is having a bad day. Live-model
behaviour is evaluated separately in Phase 08 and recorded in `AI_PLANNER.md`.

**Dependency injection via FastAPI `Depends`**, so tests never need network access or monkeypatching of
imports. If a test needs `monkeypatch` on a module-level import, the design is wrong.

## Deliberately untested

To be filled in as it arises. Every entry names what is untested, why the risk is acceptable, and what
would change that.

## Coverage

Coverage is measured but is not a gate. A percentage target produces tests written to raise a
percentage. What is gated is that failure paths are covered, checked by reading the tests.

## Running

```
uv run pytest                      # everything
uv run pytest tests/unit           # fast loop
uv run pytest --cov=app            # with coverage
```
