"""Pricing rules, shared by `GET /pricing/quote` and `POST /orders`.

Its own module deliberately. `SLOW_PRICING_MS` degrades this one function, and
because two endpoints of different shapes (a cheap read and a write) both call
it, the fault has a blast radius larger than any single route. That is precisely
the case Phase 03's coverage map exists to find and Phase 07's planner has to
reason about: a diff touching one file that slows down endpoints nobody edited.
"""

from __future__ import annotations

from typing import NamedTuple

# Volume discount in basis points, applied at the first threshold met from the
# bottom. Deliberately a pure lookup: a pricing bug here would be a correctness
# regression, and this project is about the ones tests do not catch.
_DISCOUNT_TIERS: tuple[tuple[int, int], ...] = ((20, 1_000), (10, 500), (5, 250))


class Quote(NamedTuple):
    unit_price_cents: int
    quantity: int
    discount_bps: int
    total_cents: int


def quote(unit_price_cents: int, quantity: int) -> Quote:
    """Price `quantity` units, applying the volume discount tier."""
    discount_bps = next(
        (bps for threshold, bps in _DISCOUNT_TIERS if quantity >= threshold),
        0,
    )
    gross = unit_price_cents * quantity
    total = gross - (gross * discount_bps) // 10_000
    return Quote(unit_price_cents, quantity, discount_bps, total)
