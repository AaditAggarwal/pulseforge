# FAILURE_MODES

Every failure that was reproduced, understood, and fixed. A failure does not get an entry until it has
a regression test. The point of this file is that the same class of bug cannot happen twice silently.

## Status

One failure recorded. FM-001, Phase 01.

## FM-001: structured logs silently dropped under uvicorn
Phase:        01
Discovered:   2026-08-31, by running the service for real rather than by reading the code. The
              integration suite was green and `make run` looked fine.
Reproduce:    Before the fix, with `configure_logging()` absent from `create_app`:
                uv run python -m app.target.seed
                uv run uvicorn app.target.app:create_app --factory --port 8000
                curl -s localhost:8000/health
              Then grep the server output for `target_service_started`.
Observed:     Nothing. Only uvicorn's own lines appeared:
                INFO:     Started server process [20145]
                INFO:     Application startup complete.
                INFO:     127.0.0.1:36794 - "GET /health HTTP/1.1" 200 OK
              The `target_service_started` event, which names the database and the active fault
              switches, was never emitted. No error, no warning, no traceback.
Expected:     One JSON line per the format in `app/core/logging.py`, carrying `db_path`, `pool_size`
              and `faults`.
Root cause:   `app/core/logging.py` installs its handler on the *root* logger. Uvicorn configures
              its own `uvicorn.*` loggers and leaves the root logger without a handler, so records
              from `pulseforge.*` fell through to `logging.lastResort`, which is fixed at WARNING.
              Every INFO record the service emitted was discarded. The test suite missed it because
              pytest attaches its own root handler, so under test the logs appeared correctly --
              the bug existed only under the real entrypoint.
Mitigation:   `create_app` now calls `configure_logging(resolved.log_level)` before building the
              app -- `app/target/app.py:144`. Log level comes from `PULSEFORGE_LOG_LEVEL`.
Regression:   `tests/unit/test_app_logging.py::test_create_app_installs_the_json_handler`, which
              strips the root logger the way uvicorn leaves it and asserts `create_app` puts a
              `JsonFormatter` handler back.
Worth noting: the failure mode is the dangerous kind -- absence of output rather than wrong output.
              Phase 12 would have inherited a service that logs nothing under its real entrypoint,
              and the symptom would have been "observability is broken" three phases downstream of
              the cause.

## Entry template

```
## FM-001: <short name>
Phase:        NN
Discovered:   YYYY-MM-DD, how
Reproduce:    exact steps and commands
Observed:     what actually happened, including exact error text
Expected:     what should have happened
Root cause:   the real one, not the symptom
Mitigation:   what was changed, with file and line
Regression:   the test that now fails if this returns
```
