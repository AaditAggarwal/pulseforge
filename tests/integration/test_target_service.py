"""Integration tests for the target service through the full ASGI stack.

These drive the app the way a client (and later the replay engine) will: over
HTTP, through routing and middleware. The recurring theme is that a regression
switch changes *performance or availability*, never the business result -- which
is exactly the blind spot a correctness suite has and the gate exists to cover.
"""

from __future__ import annotations

import time
from collections.abc import Sequence

import pytest
from fastapi.testclient import TestClient

from app.target import store
from app.target.app import SLOW_PRICING_DELAY_S, create_app
from app.target.config import TargetConfig


def test_health_is_ok_and_carries_correlation_id() -> None:
    with TestClient(create_app(TargetConfig())) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert resp.headers["X-Correlation-ID"]


def test_pricing_is_deterministic() -> None:
    client = TestClient(create_app(TargetConfig()))
    first = client.get("/pricing/WIDGET").json()
    second = client.get("/pricing/WIDGET").json()
    assert first == second == {"sku": "WIDGET", "price_cents": _price("WIDGET")}


def _price(sku: str) -> int:
    return sum(ord(c) for c in sku) * 10


def test_orders_result_is_identical_with_and_without_n_plus_one() -> None:
    # The N+1 switch changes how many queries run, not what comes back.
    baseline = TestClient(create_app(TargetConfig(n_plus_one=False))).get("/orders")
    regressed = TestClient(create_app(TargetConfig(n_plus_one=True))).get("/orders")
    assert baseline.status_code == regressed.status_code == 200
    assert baseline.json() == regressed.json()


def _count_queries(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, int]:
    counts = {"per_order": 0, "batched": 0}
    real_for = store.fetch_items_for
    real_batch = store.fetch_items_batch

    async def counting_for(order_id: int) -> tuple[store.LineItem, ...]:
        counts["per_order"] += 1
        return await real_for(order_id)

    async def counting_batch(
        order_ids: Sequence[int],
    ) -> dict[int, tuple[store.LineItem, ...]]:
        counts["batched"] += 1
        return await real_batch(order_ids)

    monkeypatch.setattr(store, "fetch_items_for", counting_for)
    monkeypatch.setattr(store, "fetch_items_batch", counting_batch)
    return counts


def test_baseline_issues_a_single_batched_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    counts = _count_queries(monkeypatch)
    resp = TestClient(create_app(TargetConfig(n_plus_one=False))).get("/orders")
    assert counts["batched"] == 1
    assert counts["per_order"] == 0
    assert resp.json()["count"] > 0


def test_n_plus_one_issues_one_query_per_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    counts = _count_queries(monkeypatch)
    resp = TestClient(create_app(TargetConfig(n_plus_one=True))).get("/orders")
    order_count = resp.json()["count"]
    assert counts["per_order"] == order_count  # the N+1: one query per row
    assert counts["batched"] == 0


def test_error_rate_fails_a_deterministic_fraction() -> None:
    client = TestClient(create_app(TargetConfig(error_rate=0.5)))
    statuses = [client.get("/orders").status_code for _ in range(10)]
    assert statuses.count(500) == 5
    # Evenly spaced and reproducible, not random.
    assert statuses == [200, 500] * 5


def test_health_never_fails_even_at_full_error_rate() -> None:
    client = TestClient(create_app(TargetConfig(error_rate=1.0)))
    assert all(client.get("/health").status_code == 200 for _ in range(5))


@pytest.mark.slow
def test_slow_pricing_makes_pricing_measurably_slower() -> None:
    off = TestClient(create_app(TargetConfig(slow_pricing=False)))
    on = TestClient(create_app(TargetConfig(slow_pricing=True)))

    def elapsed(client: TestClient) -> float:
        start = time.perf_counter()
        assert client.get("/pricing/WIDGET").status_code == 200
        return time.perf_counter() - start

    assert elapsed(off) < SLOW_PRICING_DELAY_S
    assert elapsed(on) >= SLOW_PRICING_DELAY_S
