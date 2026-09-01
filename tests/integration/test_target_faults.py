"""Each regression switch, proven to change behaviour through the real service.

This file is the phase's exit criterion in executable form. If a switch ever
stops changing what the service does, every verdict PulseForge produces
downstream is validated against nothing.
"""

import time
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.target.app import _fetch_items
from app.target.db import connect, initialize, seed

Factory = Callable[..., TestClient]


# --------------------------------------------------------------------------
# SLOW_PRICING_MS -- shared pricing path, so the blast radius spans two routes
# --------------------------------------------------------------------------


def _elapsed_ms(client: TestClient, method: str, url: str, **kwargs: object) -> float:
    started = time.perf_counter()
    response = client.request(method, url, **kwargs)  # type: ignore[arg-type]
    assert response.status_code in (200, 201), response.status_code
    return (time.perf_counter() - started) * 1000


@pytest.mark.slow
def test_slow_pricing_degrades_the_quote_endpoint(make_client: Factory) -> None:
    clean = _elapsed_ms(make_client(), "GET", "/pricing/quote?product_id=1&quantity=3")
    slowed = _elapsed_ms(
        make_client(slow_pricing_ms=120), "GET", "/pricing/quote?product_id=1&quantity=3"
    )
    assert slowed - clean >= 100


@pytest.mark.slow
def test_slow_pricing_also_degrades_the_write_path(make_client: Factory) -> None:
    """The fault's blast radius spans both callers of `pricing`, not one route."""
    payload = {"customer_id": 1, "items": [{"product_id": 1, "quantity": 2}]}
    clean = _elapsed_ms(make_client(), "POST", "/orders", json=payload)
    slowed = _elapsed_ms(make_client(slow_pricing_ms=120), "POST", "/orders", json=payload)
    assert slowed - clean >= 100


@pytest.mark.slow
def test_slow_pricing_leaves_unrelated_routes_alone(make_client: Factory) -> None:
    """A fault that degraded everything would make blast-radius weighting untestable."""
    slowed_client = make_client(slow_pricing_ms=120)
    assert _elapsed_ms(slowed_client, "GET", "/orders/1") < 100
    assert _elapsed_ms(slowed_client, "GET", "/health") < 100


def test_slow_pricing_does_not_change_the_response_body(make_client: Factory) -> None:
    url = "/pricing/quote?product_id=1&quantity=20"
    assert make_client().get(url).json() == make_client(slow_pricing_ms=20).get(url).json()


# --------------------------------------------------------------------------
# N_PLUS_ONE -- same bytes out, more round trips
# --------------------------------------------------------------------------


def test_n_plus_one_returns_byte_identical_responses(make_client: Factory) -> None:
    """The defining property of this regression: no correctness test can see it."""
    clean = make_client().get("/orders", params={"limit": 25})
    regressed = make_client(n_plus_one=True).get("/orders", params={"limit": 25})
    assert clean.status_code == regressed.status_code
    assert clean.content == regressed.content


async def test_n_plus_one_issues_one_query_per_order(tmp_path: Path) -> None:
    """Counted at the driver, so the claim rests on queries and not on a stopwatch."""
    db_path = tmp_path / "counted.db"
    conn = await connect(db_path)
    await initialize(conn)
    await seed(conn, products=20, orders=30, rng_seed=7)

    statements: list[str] = []
    await conn.set_trace_callback(statements.append)
    order_ids = list(range(1, 21))

    statements.clear()
    batched = await _fetch_items(conn, order_ids, n_plus_one=False)
    batched_selects = sum(1 for statement in statements if statement.lstrip().startswith("SELECT"))

    statements.clear()
    regressed = await _fetch_items(conn, order_ids, n_plus_one=True)
    regressed_selects = sum(
        1 for statement in statements if statement.lstrip().startswith("SELECT")
    )

    await conn.close()

    assert batched == regressed, "the fault must not change the rows returned"
    assert batched_selects == 1
    assert regressed_selects == len(order_ids)


def test_n_plus_one_leaves_the_single_order_read_alone(make_client: Factory) -> None:
    """One order is one query either way -- the fault must scale with page size."""
    clean = make_client().get("/orders/1")
    regressed = make_client(n_plus_one=True).get("/orders/1")
    assert clean.content == regressed.content


# --------------------------------------------------------------------------
# ERROR_RATE
# --------------------------------------------------------------------------


def test_error_rate_of_one_fails_every_request(make_client: Factory) -> None:
    client = make_client(error_rate=1.0)
    for url in ("/health", "/orders/1", "/orders", "/pricing/quote?product_id=1&quantity=1"):
        response = client.get(url)
        assert response.status_code == 500
        assert response.json() == {"detail": "injected failure"}


def test_error_rate_of_one_fails_writes_too(make_client: Factory) -> None:
    response = make_client(error_rate=1.0).post(
        "/orders", json={"customer_id": 1, "items": [{"product_id": 1, "quantity": 1}]}
    )
    assert response.status_code == 500


def test_error_rate_is_zero_by_default(make_client: Factory) -> None:
    client = make_client()
    assert all(client.get("/health").status_code == 200 for _ in range(50))


def test_partial_error_rate_produces_a_mix(make_client: Factory) -> None:
    client = make_client(error_rate=0.5, fault_seed=11)
    codes = [client.get("/health").status_code for _ in range(400)]
    assert 0.4 <= codes.count(500) / len(codes) <= 0.6
    assert 500 in codes and 200 in codes


def test_injected_errors_do_not_corrupt_the_database(make_client: Factory) -> None:
    """A failed write must leave no partial order behind."""
    before = len(make_client().get("/orders", params={"limit": 200}).json())
    failing = make_client(error_rate=1.0)
    for _ in range(5):
        failing.post(
            "/orders", json={"customer_id": 1, "items": [{"product_id": 1, "quantity": 1}]}
        )
    after = len(make_client().get("/orders", params={"limit": 200}).json())
    assert before == after


# --------------------------------------------------------------------------
# TIMEOUT_RATE
# --------------------------------------------------------------------------


@pytest.mark.slow
def test_timeout_rate_of_one_hangs_every_request(make_client: Factory) -> None:
    client = make_client(timeout_rate=1.0, timeout_sleep_ms=150)
    started = time.perf_counter()
    response = client.get("/health")
    elapsed_ms = (time.perf_counter() - started) * 1000
    assert elapsed_ms >= 140, "the fault is a hang; a fast 504 would not be one"
    assert response.status_code == 504


def test_timeout_rate_is_zero_by_default(make_client: Factory) -> None:
    assert make_client().get("/health").status_code == 200


@pytest.mark.slow
def test_error_and_timeout_can_be_injected_together(make_client: Factory) -> None:
    client = make_client(error_rate=0.5, timeout_rate=0.5, timeout_sleep_ms=1, fault_seed=3)
    codes = {client.get("/health").status_code for _ in range(100)}
    assert codes == {500, 504}, "with the rates summing to 1, no request should succeed"


async def test_fetch_items_short_circuits_on_an_empty_page(tmp_path: Path) -> None:
    """An empty page must not build an `IN ()` clause under either setting."""
    conn = await connect(tmp_path / "empty.db")
    await initialize(conn)
    assert await _fetch_items(conn, [], n_plus_one=False) == {}
    assert await _fetch_items(conn, [], n_plus_one=True) == {}
    await conn.close()
