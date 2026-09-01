"""Fault selection and injected latency, without HTTP in the way."""

import asyncio
import time
from collections import Counter

import pytest

from app.core.errors import ConfigurationError
from app.target.config import TargetSettings
from app.target.faults import Fault, FaultInjector


def _injector(**overrides: object) -> FaultInjector:
    return FaultInjector(TargetSettings(**overrides))  # type: ignore[arg-type]


def test_no_fault_is_drawn_when_both_rates_are_zero() -> None:
    injector = _injector()
    assert all(injector.draw() is None for _ in range(1_000))


def test_error_rate_of_one_always_errors() -> None:
    injector = _injector(error_rate=1.0)
    assert all(injector.draw() is Fault.ERROR for _ in range(1_000))


def test_timeout_rate_of_one_always_times_out() -> None:
    injector = _injector(timeout_rate=1.0)
    assert all(injector.draw() is Fault.TIMEOUT for _ in range(1_000))


def test_observed_rates_match_the_configured_ones() -> None:
    """A single draw picks between both faults, so neither rate distorts the other."""
    injector = _injector(error_rate=0.1, timeout_rate=0.3, fault_seed=99)
    counts = Counter(injector.draw() for _ in range(50_000))
    assert counts[Fault.ERROR] / 50_000 == pytest.approx(0.1, abs=0.01)
    assert counts[Fault.TIMEOUT] / 50_000 == pytest.approx(0.3, abs=0.01)
    assert counts[None] / 50_000 == pytest.approx(0.6, abs=0.01)


def test_rates_summing_above_one_are_rejected_at_construction() -> None:
    """Otherwise the cumulative draw would silently under-deliver timeouts."""
    with pytest.raises(ConfigurationError, match=r"must not exceed 1\.0"):
        TargetSettings(error_rate=0.7, timeout_rate=0.7)


def test_a_seed_makes_the_draw_sequence_reproducible() -> None:
    """Serial reproducibility only -- enough to make a stray injected 500 debuggable."""
    injector_a = _injector(error_rate=0.2, timeout_rate=0.2, fault_seed=5)
    injector_b = _injector(error_rate=0.2, timeout_rate=0.2, fault_seed=5)
    assert [injector_a.draw() for _ in range(200)] == [injector_b.draw() for _ in range(200)]


def test_different_seeds_diverge() -> None:
    a = _injector(error_rate=0.5, fault_seed=1)
    b = _injector(error_rate=0.5, fault_seed=2)
    assert [a.draw() for _ in range(200)] != [b.draw() for _ in range(200)]


def test_slow_pricing_is_a_no_op_when_switched_off() -> None:
    started = time.perf_counter()
    asyncio.run(_injector().slow_pricing())
    assert time.perf_counter() - started < 0.01


def test_slow_pricing_waits_for_the_configured_duration() -> None:
    started = time.perf_counter()
    asyncio.run(_injector(slow_pricing_ms=60).slow_pricing())
    assert time.perf_counter() - started >= 0.055
