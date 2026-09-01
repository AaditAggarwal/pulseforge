# BENCHMARKS

**Rules for this file.** Only numbers produced by a run that was actually executed and whose output was
pasted in. No estimates, no projections, no "approximately". Every entry records the environment, the
method, the sample count, how many warm-up requests were discarded, and the exact commands to reproduce.
Never report a mean; report p50/p95/p99 with n.

## Status

Phase 01 measured, 2026-08-31. Target service only. Nothing else exists to measure.

**Read the caveats before quoting any number below.** These are single-client, sequential,
no-concurrency measurements of a SQLite-backed service on a developer laptop under WSL2. They exist
to establish that the fault switches change behaviour by an amount the gate will be able to see.
They are not throughput numbers and they are not a claim about anything in production.

---

### B-01: clean latency profile of the target service
Date:         2026-08-31
Environment:  WSL2 (Ubuntu 26.04.1, kernel 6.6.114.1-microsoft-standard-WSL2) on Windows 11 Home.
              13th Gen Intel Core i7-13650HX, 20 logical cores visible to WSL2, 9.7 GiB RAM
              available to the VM (host RAM is capped at half per ADR-005).
              Python 3.12.13, uv 0.12.7, uvicorn 0.52.4 with uvloop 0.22.1, FastAPI 0.141.1,
              starlette 1.6.0, aiosqlite 0.22.1, SQLite 3.50.4.
Method:       One uvicorn process, `--factory`, no `--reload`. Single `httpx2` client, sequential
              requests, no concurrency. Database seeded with `rng_seed=20260101`: 200 products,
              2000 orders, 7043 order items. All four switches off.
Warm-up:      1 request per endpoint, discarded. One is enough here: the pool opens all connections
              at startup, so the only thing warming is the SQLite page cache for the pages that
              request touches.
Sample count: n = 300 per endpoint (n = 100 for `POST /orders`)
Results:
```
endpoint                       p50       p95       p99
GET  /health                0.342ms    0.535ms    0.696ms
GET  /pricing/quote         0.729ms    1.518ms    2.180ms
GET  /orders/{id}           0.948ms    1.234ms    1.566ms
GET  /orders?limit=10       1.018ms    1.379ms    1.665ms
GET  /orders?limit=50       1.536ms    2.211ms    6.749ms
GET  /orders?limit=200      3.079ms    3.950ms   12.441ms
POST /orders                1.403ms    2.336ms    3.036ms
```
Error rate:   0.000 (200/200 health checks returned 200)
Reproduce:
```
uv run python -m app.target.seed --db /tmp/pf-bench.db
uv run python scripts/phase01_evidence.py /tmp/pf-bench.db
```
Caveats:      The p99 on the two largest pages (6.7ms, 12.4ms) is roughly 3-4x their p50. That tail
              is the noise floor of this environment, not a property of the code, and ADR-004 exists
              precisely because a threshold set below it would be a gate nobody keeps switched on.
              Phase 05 must measure that floor rather than inherit this number.
              `POST /orders` grows the database as it runs, so its later samples query a slightly
              larger table than its earlier ones.

---

### B-02: each regression switch, measured against B-01
Date:         2026-08-31
Environment:  as B-01
Method:       as B-01, but one uvicorn process per configuration. Settings are read at startup, so
              a process serves exactly one configuration and no warmed cache, connection state or
              event-loop history carries between them.
Warm-up:      1 request per endpoint, discarded
Sample count: n = 20 per endpoint for the latency switches (each `SLOW_PRICING_MS` sample costs
              150ms of deliberate sleep); n = 400 for `ERROR_RATE`; n = 100 for `TIMEOUT_RATE`
Results:
```
SLOW_PRICING_MS=150
  GET /pricing/quote         p50   0.908 -> 152.374 ms   delta +151.466 ms
  POST /orders               p50   1.550 -> 153.273 ms   delta +151.723 ms
  GET /orders/{id}           p50   0.991 ->   0.771 ms   delta   -0.220 ms
  GET /health                p50   0.465 ->   0.355 ms   delta   -0.109 ms

N_PLUS_ONE=1
  GET /orders?limit=50       p50   1.850 ->   8.190 ms   delta   +6.340 ms
  GET /orders/{id}           p50   0.991 ->   0.906 ms   delta   -0.085 ms
  sha256(/orders?limit=50) identical to baseline: True

ERROR_RATE=0.25, TARGET_FAULT_SEED=42
  400 requests to /orders/42: 200 x297  500 x103
  observed error rate 0.258 (configured 0.250)

TIMEOUT_RATE=0.20, TARGET_TIMEOUT_SLEEP_MS=2000, client deadline 1s
  100 requests: 80 answered, 20 timed out client-side
  observed timeout rate 0.200 (configured 0.200)
```
Reproduce:    as B-01; the script runs every configuration in sequence
Caveats:      The two "improvements" (`-0.220 ms`, `-0.109 ms`) on unaffected routes are noise, not
              an effect. At n=20 against a p50 under 1ms, run-to-run variation of that size is
              expected; the honest reading is "unchanged", and that is exactly the kind of delta
              ADR-004's noise floor exists to refuse to call a regression.
              The observed error rate of 0.258 against a configured 0.250 is within sampling error
              for n=400 (the standard error of a 0.25 rate at n=400 is about 0.022).
              `TARGET_FAULT_SEED=42` makes these two counts reproducible for serial traffic only.
              Under concurrency the rate holds but the placement does not; see OPEN_QUESTIONS Q7.

---

### B-03: N+1 cost at the database layer
Date:         2026-08-31
Environment:  as B-01
Method:       Direct `aiosqlite` calls, no HTTP, against the seeded 2000-order database. Compares
              one batched `IN (...)` query against one indexed query per order, for a 50-order page.
Warm-up:      1 iteration, discarded
Sample count: n = 200
Results:
```
clean (1 JOIN)           p50=  0.212 ms  p95=  0.337 ms
N+1 (1 + 50 queries)     p50=  7.732 ms  p95=  9.835 ms
```
Reproduce:    the same comparison runs as a test:
              `uv run pytest tests/integration/test_target_faults.py -k n_plus_one -q`
              which asserts the query counts (1 versus 50) rather than the timings.
Caveats:      Measured before the HTTP layer existed, so it is not comparable to B-02's 6.3ms delta
              directly -- B-02 includes serialization and HTTP overhead on both sides. The two agree
              on magnitude, which is the only claim being made.

## Entry template

```
### <what was measured>
Date:         YYYY-MM-DD
Environment:  OS, kernel, CPU, RAM, Python version, container or host, WSL2 RAM cap if applicable
Method:       what was run, against what, how many requests, concurrency, seed
Warm-up:      N requests discarded, and why that N
Sample count: n = ...
Results:      p50 / p95 / p99, error rate
Raw output:   pasted, verbatim
Reproduce:    exact commands
Caveats:      anything that would make a reader distrust the number
```
