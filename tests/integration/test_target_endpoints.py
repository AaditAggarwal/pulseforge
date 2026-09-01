"""The five endpoints against a real seeded database, faults all off.

These are the clean profiles every later phase compares against, so they are
asserted on behaviour, not on timing -- timing evidence belongs in BENCHMARKS.md.
"""

import pytest
from fastapi.testclient import TestClient


def test_health_is_cheap_and_touches_no_database(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_order_returns_the_order_with_its_items(client: TestClient) -> None:
    body = client.get("/orders/1").json()
    assert body["id"] == 1
    assert len(body["items"]) >= 1
    assert body["total_cents"] == sum(
        item["quantity"] * item["unit_price_cents"] for item in body["items"]
    )


def test_get_order_404s_for_a_missing_id(client: TestClient) -> None:
    assert client.get("/orders/999999").status_code == 404


def test_list_orders_size_follows_limit(client: TestClient) -> None:
    assert len(client.get("/orders", params={"limit": 5}).json()) == 5
    assert len(client.get("/orders", params={"limit": 40}).json()) == 40


def test_list_orders_rejects_an_oversized_page(client: TestClient) -> None:
    assert client.get("/orders", params={"limit": 5000}).status_code == 422


def test_list_orders_offset_pages_without_overlap(client: TestClient) -> None:
    first = {order["id"] for order in client.get("/orders", params={"limit": 10}).json()}
    second = {
        order["id"] for order in client.get("/orders", params={"limit": 10, "offset": 10}).json()
    }
    assert first.isdisjoint(second)


def test_every_listed_order_carries_its_items(client: TestClient) -> None:
    orders = client.get("/orders", params={"limit": 20}).json()
    assert all(order["items"] for order in orders)


def test_pricing_quote_applies_the_volume_discount(client: TestClient) -> None:
    single = client.get("/pricing/quote", params={"product_id": 1, "quantity": 1}).json()
    bulk = client.get("/pricing/quote", params={"product_id": 1, "quantity": 20}).json()
    assert single["discount_bps"] == 0
    assert bulk["discount_bps"] == 1000
    assert bulk["total_cents"] < single["unit_price_cents"] * 20


def test_pricing_quote_404s_for_a_missing_product(client: TestClient) -> None:
    assert (
        client.get("/pricing/quote", params={"product_id": 99999, "quantity": 1}).status_code == 404
    )


def test_create_order_persists_and_is_readable_back(client: TestClient) -> None:
    payload = {
        "customer_id": 3,
        "items": [{"product_id": 1, "quantity": 2}, {"product_id": 2, "quantity": 5}],
    }
    created = client.post("/orders", json=payload)
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "pending"
    assert len(body["items"]) == 2
    assert client.get(f"/orders/{body['id']}").json() == body


def test_create_order_prices_through_the_shared_pricing_module(client: TestClient) -> None:
    """The write path and the quote path must agree, or the fault's blast
    radius would not actually span both."""
    quoted = client.get("/pricing/quote", params={"product_id": 1, "quantity": 5}).json()
    created = client.post(
        "/orders", json={"customer_id": 1, "items": [{"product_id": 1, "quantity": 5}]}
    ).json()
    assert created["total_cents"] == quoted["total_cents"]


def test_create_order_404s_for_an_unknown_product(client: TestClient) -> None:
    response = client.post(
        "/orders", json={"customer_id": 1, "items": [{"product_id": 99999, "quantity": 1}]}
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {"customer_id": 1, "items": []},
        {"customer_id": 0, "items": [{"product_id": 1, "quantity": 1}]},
        {"customer_id": 1, "items": [{"product_id": 1, "quantity": 0}]},
        {"items": [{"product_id": 1, "quantity": 1}]},
    ],
)
def test_create_order_rejects_invalid_payloads(client: TestClient, payload: dict) -> None:
    assert client.post("/orders", json=payload).status_code == 422
