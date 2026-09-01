"""Volume-discount rules. Pure function, so no fixtures and no I/O."""

import pytest

from app.target.pricing import quote


@pytest.mark.parametrize(
    ("quantity", "expected_bps"),
    [(1, 0), (4, 0), (5, 250), (9, 250), (10, 500), (19, 500), (20, 1000), (100, 1000)],
)
def test_discount_tier_boundaries(quantity: int, expected_bps: int) -> None:
    assert quote(1_000, quantity).discount_bps == expected_bps


def test_total_applies_the_discount() -> None:
    result = quote(1_000, 20)
    assert result.total_cents == 20_000 - 2_000


def test_no_discount_is_plain_multiplication() -> None:
    assert quote(333, 3).total_cents == 999


def test_discount_rounds_down_never_up() -> None:
    """Integer cents. Rounding up would let the service overcharge."""
    assert quote(101, 5).total_cents == 505 - 12  # 505 * 0.025 = 12.625 -> 12
