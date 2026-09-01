# Phase 02 — CAPTURE

> **Status: not started.** Scope and files set 2026-08-31 at the close of Phase 01.

## Goal

Record live traffic through ASGI middleware and sanitize it deny-by-default before any byte reaches disk.

## Why this exists

PulseForge cannot replay traffic it has not recorded. This phase produces the corpus every later
phase consumes, and it is the phase where the security boundary lives: sanitization happens inside
the write path, so raw traffic never reaches a filesystem. A capture bug that writes a secret is not
a bug to be fixed later — the raw write is the incident.

## Relevant decisions

- ADR-001 — capture is in-process ASGI middleware; route templates and handler identity come free,
  sanitization happens before the first byte is written
- ADR-002 — content-addressed files plus JSONL manifests behind an `app/storage` seam
- Q2 in `OPEN_QUESTIONS.md` — inline request bodies versus content-addressing them separately.
  Resolve it in this phase.

## Files in scope

Existing, to read:
- `app/core/errors.py` — `CaptureError`, `SanitizationError`, `StorageError` already exist
- `app/core/logging.py` — correlation IDs, already threaded through contextvars
- `app/target/app.py` — the service the middleware will be mounted on
- `docs/SECURITY.md` and `docs/DATA_POLICY.md` — the sanitization contract this phase implements

New, to write:
- `app/capture/middleware.py` — the ASGI middleware
- `app/capture/sanitize.py` — deny-by-default redaction, fail-closed
- `app/capture/corpus.py` — the `CapturedRequest` model and JSONL writing
- `app/storage/` — content addressing and the filesystem seam
- `tests/unit/test_sanitize.py`, `tests/property/test_sanitize_properties.py`
- `tests/integration/test_capture_against_target.py`

## Notes carried in from Phase 01

- The target service reads its settings once at startup and serves exactly one configuration, so a
  corpus can be attributed to a known fault configuration without ambiguity.
- Seed data is deterministic given `rng_seed`, so a corpus recorded against one seeded database stays
  valid against another built the same way.
- `POST /orders` writes, which means a captured corpus contains writes. That is Q4's problem, not this
  phase's, but capture must record enough for Phase 04 to have the option of replaying them.
- Capture overhead must be measured against `BENCHMARKS.md` B-01, which is the uninstrumented
  baseline for exactly this comparison. ADR-001 requires capture to be disableable and its overhead
  known.

## Exit criteria

- [ ] Feature works, with pasted output proving it
- [ ] Unit tests pass and cover failure paths, not only the happy path
- [ ] Integration test exists where this phase crosses a component boundary
- [ ] `ruff check`, `ruff format --check`, and `mypy --strict app/` all clean
- [ ] One deliberate failure injected, observed, and recorded in `FAILURE_MODES.md`
- [ ] Docs updated per the trigger table
- [ ] Any measured numbers in `BENCHMARKS.md` with reproduction steps
- [ ] Commit commands printed and run
- [ ] Next phase doc updated with its scope list
