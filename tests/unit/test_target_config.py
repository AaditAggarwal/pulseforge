"""Unit tests for the target service's regression-switch config parsing."""

from __future__ import annotations

import pytest

from app.target.config import TargetConfig


def test_defaults_are_the_baseline() -> None:
    cfg = TargetConfig()
    assert cfg.slow_pricing is False
    assert cfg.n_plus_one is False
    assert cfg.error_rate == 0.0


def test_from_env_reads_all_switches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLOW_PRICING", "1")
    monkeypatch.setenv("N_PLUS_ONE", "true")
    monkeypatch.setenv("ERROR_RATE", "0.25")
    cfg = TargetConfig.from_env()
    assert cfg == TargetConfig(slow_pricing=True, n_plus_one=True, error_rate=0.25)


def test_from_env_defaults_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("SLOW_PRICING", "N_PLUS_ONE", "ERROR_RATE"):
        monkeypatch.delenv(name, raising=False)
    assert TargetConfig.from_env() == TargetConfig()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1", True),
        ("true", True),
        ("YES", True),
        ("on", True),
        ("0", False),
        ("false", False),
        ("", False),
        ("nonsense", False),
    ],
)
def test_bool_parsing(monkeypatch: pytest.MonkeyPatch, raw: str, expected: bool) -> None:
    monkeypatch.setenv("SLOW_PRICING", raw)
    assert TargetConfig.from_env().slow_pricing is expected


@pytest.mark.parametrize("value", ["-0.1", "1.5", "abc", "1e9"])
def test_error_rate_rejects_out_of_range_or_garbage(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("ERROR_RATE", value)
    with pytest.raises(ValueError):
        TargetConfig.from_env()


def test_error_rate_boundaries_are_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ERROR_RATE", "0.0")
    assert TargetConfig.from_env().error_rate == 0.0
    monkeypatch.setenv("ERROR_RATE", "1.0")
    assert TargetConfig.from_env().error_rate == 1.0
