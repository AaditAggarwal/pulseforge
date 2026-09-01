# Phase 01 — TARGET SERVICE

> **Status: complete.** 2026-08-31.

## Goal

A small FastAPI service with endpoints of genuinely different cost profiles and four
runtime-switchable regressions (`SLOW_PRICING_MS`, `N_PLUS_ONE`, `ERROR_RATE`, `TIMEOUT_RATE`), so
every later phase has ground truth to verify against.

## Why this exists

Nothing downstream is verifiable without it. A capture pipeline that records nothing real, a replay
engine with no service to replay against, and a gate with no known regression to catch are all
untestable. This phase produces the only thing in the repository whose behaviour we control exactly,
which makes it the measuring stick for everything else.

**Why the regressions are runtime switches rather than a branch.** This is the load-bearing decision
of the phase.

1. *One variable.* The gate's claim is "this diff caused this latency delta". If the fault lived on a
   branch, baseline and candidate would differ by that branch's entire diff plus a separate build, and
   the delta could not be attributed. With a flag the artifact is byte-identical on both sides and the
   only difference is one environment variable.
2. *A real negative control.* ADR-004 requires a baseline-vs-baseline run to measure the noise floor,
   and the gate must return PASS when nothing changed. "Nothing changed" is only meaningful if the
   no-regression case is the same binary as the regression case.
3. *The fault is a parameter, not an event.* `SLOW_PRICING_MS=5` versus `=200` sweeps magnitude, which
   is how Phase 05 will find the gate's detection threshold — the smallest regression distinguishable
   from the noise floor. A branch hardcodes one slowdown and can only answer yes/no.
4. *Branches rot, flags refactor.* Every future change to `app/target` would need N regression branches
   rebased. The day one silently fails to rebase, ground truth is stale and nothing announces it.
5. *R7 stays enforceable.* A flag changes how long a handler takes, never its contract, so a corpus
   captured once stays valid. A branch could change the routes themselves and invalidate it.

**What this buys in Phase 08.** Phase 08 asks whether diff-aware weighting beats random sampling at
equal request budget. Answering that empirically needs a population of regressions with known ground
truth — which endpoint, how large, how rare — and many trials per configuration, because `ERROR_RATE`
and `TIMEOUT_RATE` are probabilistic and one trial says nothing. Runtime flags make the fault space
programmatically enumerable: the eval harness is a loop over `(fault, magnitude)` environment dicts,
not a `git checkout` and rebuild per trial. It also gives Phase 08 a sharper metric than verdict
outcome — because the fault's location is known by construction, the planner's *budget allocation* can
be scored directly (did it spend requests on the pricing path when `SLOW_PRICING_MS` was set?).

## Relevant decisions

- ADR-001 — capture is in-process ASGI middleware, so the target must be a Python ASGI service
- ADR-004 — regression as delta against a measured noise floor; drives the need for magnitude sweeps
- ADR-005 — WSL2 on the Linux filesystem; every number in `BENCHMARKS.md` carries that caveat
- ADR-006 — Python 3.12, uv, ruff, `mypy --strict` on `app/`

No new ADR was required. Nothing here changed a decision; the switch-versus-branch reasoning is design
inside an existing decision, recorded above rather than as an ADR.

## What was built

| Route | Cost profile |
|---|---|
| `GET /health` | cheap, no database, constant work |
| `GET /pricing/quote` | one indexed row read plus a pure computation |
| `GET /orders/{id}` | two indexed reads, fixed size |
| `GET /orders?limit=N` | variable-size collection, cost scales with N |
| `POST /orders` | write, multi-statement transaction |

| Switch | Effect | Blast radius |
|---|---|---|
| `SLOW_PRICING_MS` | `asyncio.sleep` on the shared pricing path | `GET /pricing/quote` **and** `POST /orders` |
| `N_PLUS_ONE` | one indexed query per order instead of one batched query | `GET /orders` only; scales with page size |
| `ERROR_RATE` | probability a request returns 500, drawn in middleware | uniform across every route |
| `TIMEOUT_RATE` | probability a request hangs past the client deadline | uniform across every route |

Pricing lives in its own module called by two routes of different shapes, so the fault has a blast
radius wider than any single endpoint. That is the case Phase 03's coverage map exists to find and
Phase 07's planner has to reason about: a diff touching one file that slows down routes nobody edited.

## Files in scope

- `app/target/config.py` — frozen settings parsed from environment at startup
- `app/target/db.py` — schema, deterministic seed, connection pool
- `app/target/seed.py` — `python -m app.target.seed`
- `app/target/pricing.py` — shared volume-discount rules
- `app/target/faults.py` — every injected behaviour, in one file
- `app/target/app.py` — app factory, lifespan, the five endpoints
- `scripts/phase01_evidence.py` — reproduces the `BENCHMARKS.md` numbers
- `tests/unit/test_target_config.py`, `test_pricing.py`, `test_faults.py`, `test_app_logging.py`
- `tests/integration/conftest.py`, `test_target_db.py`, `test_target_endpoints.py`, `test_target_faults.py`

## Design notes worth carrying forward

- **Settings are read once at startup and never mutated.** Reconfiguring means restarting the process.
  Flipping a switch inside a live process would carry warmed caches and connection state across the
  baseline/candidate boundary, restoring the confounder runtime switching exists to remove.
- **One uniform draw** picks between error, timeout and neither, so the configured probabilities are
  the observed ones exactly. Two independent draws would deliver `(1 - error_rate) x timeout_rate`
  timeouts. The cost: `ERROR_RATE + TIMEOUT_RATE > 1.0` is a startup error.
- **`order_items(order_id)` is indexed**, so the injected N+1 costs one cheap query per row as a real
  ORM lazy-load does. Dropping the index would make the fault enormous and prove nothing about the
  gate's sensitivity.
- **Raw ASGI middleware, not `BaseHTTPMiddleware`**, which wraps every request in a task group and
  buffers the response whether or not a fault fires. Overhead in the injection layer would land
  directly in the numbers the gate compares.
- **`SLOW_PRICING_MS` models added I/O wait, not CPU.** A CPU-bound regression would also degrade
  concurrent requests by blocking the event loop. Different failure shape; it would need its own switch.
- **`POST /orders` prices once per line item**, so a 20-item order takes 20x the injected latency.
  Deliberate — it gives the fault a payload-dependent blast radius — but Phase 05 must not be
  surprised by it.

## Exit criteria

- [x] Feature works, with pasted output proving it — `BENCHMARKS.md`, Phase 01 entries
- [x] Unit tests pass and cover failure paths, not only the happy path — 113 tests, 99% on `app/target`
- [x] Integration test exists where this phase crosses a component boundary — `tests/integration/`
- [x] `ruff check`, `ruff format --check`, and `mypy --strict app/` all clean
- [x] One deliberate failure injected, observed, and recorded in `FAILURE_MODES.md` — FM-001
- [x] Docs updated per the trigger table
- [x] Any measured numbers in `BENCHMARKS.md` with reproduction steps
- [ ] Commit commands printed and run
- [x] Next phase doc updated with its scope list
