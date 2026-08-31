# CONTRIBUTING

This is currently a solo project. These are the rules it is built under, recorded so they stay
consistent.

## Licensing

PulseForge is under the Business Source License 1.1 (ADR-003), which is not an OSI-approved open source
license. Outside contributions are not being accepted at this time, because accepting them without a
CLA would make future relicensing impossible.

## Branching

`main` is protected and always green. Work happens on `phase-XX/short-description`, merged via PR,
squashed, branch deleted.

## Commits

Conventional Commits, present tense, one logical change each.

```
feat(replay): add concurrent replay with bounded semaphore
fix(sanitize): strip Set-Cookie on redirect responses
test(planner): assert plan hash stability across runs
docs(adr): record ADR-012 queue selection
infra(terraform): provision replay queue and DLQ
ci(gate): fail workflow on BLOCK verdict
```

Never `update`, `stuff`, `wip`, `final2`. Always stage files explicitly. Never `git add .` — that is
how secrets get committed.

## Before opening a PR

- `uv run ruff check .` and `uv run ruff format --check .` clean
- `uv run mypy --strict app/` clean
- `uv run pytest` green, including failure-path tests
- No secrets in the diff; gitleaks passes
- Documentation updated per the trigger table in `docs/PROJECT_CONTEXT.md`
- Any measured number recorded in `docs/BENCHMARKS.md` with reproduction steps

## Hard rules

- No fabricated numbers anywhere in this repository. If it was not measured, it says `NOT YET MEASURED`.
- No secrets, credentials, PII, or real captured traffic. Synthetic fixtures only.
- Every artifact carries `schema_version`.
- Every stochastic element takes an explicit seed.
