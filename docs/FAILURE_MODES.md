# FAILURE_MODES

Every failure that was reproduced, understood, and fixed. A failure does not get an entry until it has
a regression test. The point of this file is that the same class of bug cannot happen twice silently.

## FM-001: baseline demo ran against another process's server on port 8000
Phase:        01
Discovered:   2026-08-31, during the live SLOW_PRICING demonstration
Reproduce:    start `uv run uvicorn app.target.app:create_app --factory --port 8000` while another
              process already listens on 127.0.0.1:8000
Observed:     uvicorn logged `[Errno 48] error while attempting to bind on address ('127.0.0.1',
              8000): address already in use` and exited; `curl :8000/health` then returned
              `{"detail":"Not Found"}` (a 404 from the pre-existing process), which looked like our
              own app misrouting every endpoint
Expected:     the demo to exercise our service, or fail loudly, rather than appear to run against the
              wrong server
Root cause:   port 8000 was already bound by an unrelated local Python process; the readiness loop
              treated any HTTP response — including the foreign 404 — as "service is up"
Mitigation:   ran the demo on free ports; the readiness check now asserts the `/health` body is
              `{"status": "ok"}`, not merely that some response came back
Regression:   tests/integration/test_target_service.py::test_health_is_ok_and_carries_correlation_id
              pins the exact `/health` contract, so a foreign server answering would not satisfy it

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
