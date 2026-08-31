# RUNBOOK

How to operate PulseForge: start, stop, deploy, roll back, diagnose.

## Status

Nothing to operate yet. Populated as each phase produces something runnable.

## Development environment

```
uv sync                            # create the locked environment
uv run pytest                      # run tests
uv run ruff check .                # lint
uv run ruff format .               # format
uv run mypy --strict app/          # type check
uv run pre-commit run --all-files  # everything the hook would run
```
