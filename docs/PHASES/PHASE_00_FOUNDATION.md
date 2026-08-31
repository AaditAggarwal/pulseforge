# Phase 00 — Foundation

> **Status: in progress.** Started 2026-08-30.

## Goal

Establish the repository, toolchain, documentation system, and CI skeleton, and record the
architectural decisions that are expensive to reverse. No application code is written in this phase.

## Why this exists

Three things are effectively impossible to retrofit and are therefore decided now, before there is any
code to migrate: structured logging with correlation IDs, `schema_version` on every artifact, and the
license. A CI skeleton exists from the first commit for the same reason — a CI pipeline added at Phase
10 will be a pipeline that has never once blocked anything.

## Relevant decisions

- ADR-001 capture mechanism (constrains `app/target` and `app/capture`)
- ADR-002 artifact storage (constrains `app/storage` and the directory layout)
- ADR-003 license (constrains `LICENSE`, `README.md`, and file headers)
- ADR-006 toolchain (constrains `pyproject.toml`, `.pre-commit-config.yaml`, CI)
- ADR-005 development environment — Accepted; migration to WSL2 is Task 1b.

## Files in scope

```
pyproject.toml
.pre-commit-config.yaml
.gitignore
.env.example
Makefile
.github/workflows/ci.yml
docs/**            (created in this phase)
README.md  CHANGELOG.md  LICENSE  CONTRIBUTING.md
app/__init__.py
tests/{unit,property,integration,e2e}/.gitkeep
```

`app/__init__.py` exists only so hatchling has a package to build and `pytest` has something to
import. It contains a docstring and nothing else. Real code starts in Phase 01.

## Tasks

| # | Task | Status |
|---|---|---|
| 0 | Documentation tree, ADR-001..006, root docs | done |
| 1 | `pyproject.toml` — project metadata, dependencies, ruff, mypy, pytest config | written, unverified |
| 1b | Migrate to WSL2 per ADR-005, then verify Task 1 with `uv sync` | **current** |
| 2 | `.pre-commit-config.yaml` with ruff and gitleaks; verify gitleaks catches a planted secret | pending |
| 3 | `.github/workflows/ci.yml` — lint, type check, test, `pip-audit`, fixture entropy scan | pending |
| 4 | `Makefile` and `.env.example`; package skeleton with `app/core/errors.py` and structured logging | pending |

Tasks 2-4 are provisional and may change based on what Task 1 reveals.

## Exit criteria

- [ ] `uv sync` produces a locked environment on Python 3.12, and `uv.lock` is committed
- [ ] `uv run ruff check .` and `uv run ruff format --check .` pass on an empty tree
- [ ] `uv run mypy --strict app/` passes (trivially, with no source yet)
- [ ] `uv run pytest` runs and reports zero tests without erroring
- [ ] `pre-commit run --all-files` passes
- [ ] gitleaks demonstrably blocks a deliberately planted fake secret, and that observation is recorded
      in `FAILURE_MODES.md`
- [ ] CI workflow runs green on a pushed branch, with the run URL recorded
- [x] ADR-005 resolved: accepted; repo moved to WSL2 Linux filesystem
- [ ] `PROJECT_CONTEXT.md` status table reflects reality
- [ ] `PHASE_01_TARGET_SERVICE.md` filled in with its scope list
- [ ] Commit commands printed and run

## Deliberate failure for this phase

Plant a realistic-looking fake AWS key in a file, attempt to commit, and confirm gitleaks blocks it.
This proves the secret-scanning boundary works before there is any real traffic data to leak. Record
the observed behaviour in `FAILURE_MODES.md`.
