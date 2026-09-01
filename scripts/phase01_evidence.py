"""Reproduce the Phase 01 numbers in BENCHMARKS.md.

    uv run python -m app.target.seed --db /tmp/pf-bench.db
    uv run python scripts/phase01_evidence.py /tmp/pf-bench.db

One uvicorn process per configuration, on purpose: settings are read at startup,
so a process serves exactly one configuration and nothing carries over between
them -- no warmed caches, no connection state, no event-loop history. That is
the same property that makes the switches usable as gate fixtures at all.

Not a test and not part of `app/`. It exists so the numbers in BENCHMARKS.md can
be re-run by someone who does not believe them.
"""

import hashlib
import os
import statistics
import subprocess
import sys
import time

import httpx2 as httpx

BASE = "http://127.0.0.1:8011"
DB = sys.argv[1]


def boot(env_overrides):
    env = {**os.environ, "TARGET_DB_PATH": DB, **env_overrides}
    proc = subprocess.Popen(
        [
            "uv",
            "run",
            "uvicorn",
            "app.target.app:create_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            "8011",
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(80):
        try:
            httpx.get(f"{BASE}/health", timeout=1.0)
            return proc
        except Exception:
            time.sleep(0.25)
    proc.terminate()
    raise RuntimeError("service did not come up")


def percentiles(samples):
    samples = sorted(samples)

    def pick(q):
        return samples[min(int(q * len(samples)), len(samples) - 1)]

    return statistics.median(samples), pick(0.95)


def timed(client, method, url, n=200, **kw):
    client.request(method, url, **kw)
    samples = []
    for _ in range(n):
        t = time.perf_counter_ns()
        client.request(method, url, **kw)
        samples.append((time.perf_counter_ns() - t) / 1e6)
    return percentiles(samples)


def row(label, clean, faulty):
    delta = faulty[0] - clean[0]
    mark = "  <-- degraded" if delta > 1.0 else ""
    print(
        f"  {label:26s} p50 {clean[0]:7.3f} -> {faulty[0]:7.3f} ms   delta {delta:+8.3f} ms{mark}"
    )


ORDER = {"customer_id": 1, "items": [{"product_id": 1, "quantity": 2}]}

print("=" * 78)
print("BASELINE: all switches off")
print("=" * 78)
proc = boot({})
with httpx.Client(timeout=30.0) as c:
    base_quote = timed(c, "GET", f"{BASE}/pricing/quote?product_id=7&quantity=3")
    base_write = timed(c, "POST", f"{BASE}/orders", n=100, json=ORDER)
    base_one = timed(c, "GET", f"{BASE}/orders/42")
    base_list = timed(c, "GET", f"{BASE}/orders?limit=50")
    base_health = timed(c, "GET", f"{BASE}/health")
    base_list_body = hashlib.sha256(c.get(f"{BASE}/orders?limit=50").content).hexdigest()
    base_ok = sum(c.get(f"{BASE}/health").status_code == 200 for _ in range(200))
proc.terminate()
proc.wait()
for label, v in [
    ("GET /health", base_health),
    ("GET /pricing/quote", base_quote),
    ("GET /orders/{id}", base_one),
    ("GET /orders?limit=50", base_list),
    ("POST /orders", base_write),
]:
    print(f"  {label:26s} p50 {v[0]:7.3f} ms   p95 {v[1]:7.3f} ms")
print(f"  200/200 health checks OK: {base_ok == 200}")
print(f"  sha256(/orders?limit=50) = {base_list_body[:32]}...")

print()
print("=" * 78)
print("SLOW_PRICING_MS=150")
print("=" * 78)
proc = boot({"SLOW_PRICING_MS": "150"})
with httpx.Client(timeout=30.0) as c:
    quote_url = f"{BASE}/pricing/quote?product_id=7&quantity=3"
    row("GET /pricing/quote", base_quote, timed(c, "GET", quote_url, n=20))
    row("POST /orders", base_write, timed(c, "POST", f"{BASE}/orders", n=20, json=ORDER))
    row("GET /orders/{id}", base_one, timed(c, "GET", f"{BASE}/orders/42", n=20))
    row("GET /health", base_health, timed(c, "GET", f"{BASE}/health", n=20))
proc.terminate()
proc.wait()
print("  blast radius: both callers of app/target/pricing.py, nothing else")

print()
print("=" * 78)
print("N_PLUS_ONE=1")
print("=" * 78)
proc = boot({"N_PLUS_ONE": "1"})
with httpx.Client(timeout=30.0) as c:
    row("GET /orders?limit=50", base_list, timed(c, "GET", f"{BASE}/orders?limit=50"))
    row("GET /orders/{id}", base_one, timed(c, "GET", f"{BASE}/orders/42"))
    faulty_body = hashlib.sha256(c.get(f"{BASE}/orders?limit=50").content).hexdigest()
proc.terminate()
proc.wait()
print(f"  sha256(/orders?limit=50) = {faulty_body[:32]}...")
print(f"  response bytes identical to baseline: {faulty_body == base_list_body}")

print()
print("=" * 78)
print("ERROR_RATE=0.25")
print("=" * 78)
proc = boot({"ERROR_RATE": "0.25", "TARGET_FAULT_SEED": "42"})
with httpx.Client(timeout=30.0) as c:
    codes = [c.get(f"{BASE}/orders/42").status_code for _ in range(400)]
proc.terminate()
proc.wait()
print(f"  400 requests to /orders/42: 200 x{codes.count(200)}  500 x{codes.count(500)}")
print(f"  observed error rate {codes.count(500) / len(codes):.3f} (configured 0.250)")
print(f"  baseline error rate 0.000 ({base_ok}/200 OK)")

print()
print("=" * 78)
print("TIMEOUT_RATE=0.20, TARGET_TIMEOUT_SLEEP_MS=2000, client deadline 1s")
print("=" * 78)
proc = boot({"TIMEOUT_RATE": "0.2", "TARGET_TIMEOUT_SLEEP_MS": "2000", "TARGET_FAULT_SEED": "42"})
hung = ok = 0
with httpx.Client(timeout=1.0) as c:
    for _ in range(100):
        try:
            c.get(f"{BASE}/health")
            ok += 1
        except httpx.TimeoutException:
            hung += 1
proc.terminate()
proc.wait()
print(f"  100 requests, 1s client deadline: {ok} answered, {hung} timed out client-side")
print(f"  observed timeout rate {hung / 100:.3f} (configured 0.200)")
