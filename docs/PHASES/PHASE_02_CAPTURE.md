# Phase 02 — CAPTURE

> **Status: not started.** Stub. Fill in scope and design only when this phase begins.

## Goal

Record live traffic through ASGI middleware and sanitize it deny-by-default before any byte reaches disk.

## Why this exists

To be written when the phase begins.

## Relevant decisions

To be listed when the phase begins. Read only the ADRs named here.

## Files in scope

Anticipated (to be confirmed when the phase begins):

- `app/capture/__init__.py`, `app/capture/middleware.py` — the ASGI capture middleware
- `app/capture/sanitize.py` — deny-by-default header allowlist + body redaction (SECURITY.md)
- `app/storage/__init__.py`, `app/storage/corpus.py` — content-addressed corpus writing (ADR-002)
- `tests/unit/test_sanitize.py` — property-based (`hypothesis`) tests on the sanitizer
- `tests/integration/test_capture.py` — capture running against the Phase 01 target service

Runs against the Phase 01 target service (`app/target`). If a session needs a file not listed here,
ask before reading it, then add it to this list.

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
