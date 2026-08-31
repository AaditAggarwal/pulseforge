"""An in-memory stand-in for a database, with a deliberate N+1 access pattern.

Each simulated query costs ``QUERY_LATENCY_S`` to model a database round trip,
so the N+1 regression shows up as measurable latency the gate can detect. The
dataset is small and fixed on purpose: replay must be reproducible. This is a
test subject, not a real data layer.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass

# One simulated database round trip. Small enough to keep the suite fast, large
# enough that N per-row queries dominate a single batched query.
QUERY_LATENCY_S = 0.002


@dataclass(frozen=True, slots=True)
class LineItem:
    sku: str
    quantity: int
    unit_price_cents: int


@dataclass(frozen=True, slots=True)
class Order:
    order_id: int
    customer: str


_ORDERS: tuple[Order, ...] = tuple(
    Order(order_id=i, customer=f"customer-{i % 7}") for i in range(1, 13)
)

_ITEMS: dict[int, tuple[LineItem, ...]] = {
    order.order_id: tuple(
        LineItem(
            sku=f"SKU-{order.order_id}-{j}",
            quantity=j + 1,
            unit_price_cents=500 * (j + 1),
        )
        for j in range(3)
    )
    for order in _ORDERS
}


async def fetch_orders() -> tuple[Order, ...]:
    """One query for the order list."""
    await asyncio.sleep(QUERY_LATENCY_S)
    return _ORDERS


async def fetch_items_for(order_id: int) -> tuple[LineItem, ...]:
    """One query for a single order's items -- the per-row query in an N+1."""
    await asyncio.sleep(QUERY_LATENCY_S)
    return _ITEMS.get(order_id, ())


async def fetch_items_batch(order_ids: Sequence[int]) -> dict[int, tuple[LineItem, ...]]:
    """One query for every order's items at once -- the batched, non-N+1 path."""
    await asyncio.sleep(QUERY_LATENCY_S)
    return {order_id: _ITEMS.get(order_id, ()) for order_id in order_ids}
