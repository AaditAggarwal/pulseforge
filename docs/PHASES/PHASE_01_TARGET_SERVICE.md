# Phase 01 — TARGET SERVICE

> **Status: not started.** Stub. Fill in scope and design only when this phase begins.

## Goal

Build a small FastAPI service with switchable, deliberate regressions (`SLOW_PRICING`, `N_PLUS_ONE`, `ERROR_RATE`) so every later phase has ground truth to verify against.

## Why this exists

To be written when the phase begins.

## Relevant decisions

To be listed when the phase begins. Read only the ADRs named here.

## Files in scope

To be listed when the phase begins. If a session needs a file not listed here,
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
