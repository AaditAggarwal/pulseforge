"""Parsing and validation of the target service's regression switches.

These switches are the ground truth for every later phase, so a silently
misparsed value would corrupt every measurement downstream. Invalid input must
fail loudly at startup.
"""

from pathlib import Path

import pytest

from app.core.errors import ConfigurationError
from app.target.config import TargetSettings


def test_defaults_are_all_faults_off() -> None:
    settings = TargetSettings.from_env({})
    assert settings.slow_pricing_ms == 0
    assert settings.n_plus_one is False
    assert settings.error_rate == 0.0
    assert settings.timeout_rate == 0.0
    assert settings.faults_enabled is False
    assert settings.active_faults == {}


def test_all_switches_parsed_from_env() -> None:
    settings = TargetSettings.from_env(
        {
            "SLOW_PRICING_MS": "250",
            "N_PLUS_ONE": "1",
            "ERROR_RATE": "0.05",
            "TIMEOUT_RATE": "0.01",
            "TARGET_DB_PATH": "custom/target.db",
            "TARGET_TIMEOUT_SLEEP_MS": "5000",
        }
    )
    assert settings.slow_pricing_ms == 250
    assert settings.n_plus_one is True
    assert settings.error_rate == 0.05
    assert settings.timeout_rate == 0.01
    assert settings.db_path == Path("custom/target.db")
    assert settings.timeout_sleep_ms == 5000
    assert settings.faults_enabled is True
    assert settings.active_faults == {
        "SLOW_PRICING_MS": 250,
        "N_PLUS_ONE": True,
        "ERROR_RATE": 0.05,
        "TIMEOUT_RATE": 0.01,
    }


def test_settings_are_immutable() -> None:
    settings = TargetSettings.from_env({})
    with pytest.raises((AttributeError, TypeError)):
        settings.slow_pricing_ms = 100  # type: ignore[misc]


@pytest.mark.parametrize("raw", ["", "   "])
def test_blank_value_means_default_not_error(raw: str) -> None:
    assert TargetSettings.from_env({"SLOW_PRICING_MS": raw}).slow_pricing_ms == 0


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1", True),
        ("true", True),
        ("YES", True),
        ("on", True),
        ("0", False),
        ("false", False),
        ("no", False),
        ("Off", False),
    ],
)
def test_bool_accepts_common_spellings(raw: str, expected: bool) -> None:
    assert TargetSettings.from_env({"N_PLUS_ONE": raw}).n_plus_one is expected


@pytest.mark.parametrize("raw", ["maybe", "2", "1.0", "-1"])
def test_invalid_bool_rejected(raw: str) -> None:
    with pytest.raises(ConfigurationError, match="N_PLUS_ONE"):
        TargetSettings.from_env({"N_PLUS_ONE": raw})


@pytest.mark.parametrize("raw", ["abc", "1.5", "10ms", "1e"])
def test_invalid_int_rejected(raw: str) -> None:
    with pytest.raises(ConfigurationError, match="SLOW_PRICING_MS"):
        TargetSettings.from_env({"SLOW_PRICING_MS": raw})


def test_negative_slowdown_rejected() -> None:
    with pytest.raises(ConfigurationError, match=">= 0"):
        TargetSettings.from_env({"SLOW_PRICING_MS": "-1"})


@pytest.mark.parametrize("name", ["ERROR_RATE", "TIMEOUT_RATE"])
@pytest.mark.parametrize("raw", ["-0.1", "1.5", "100", "half"])
def test_out_of_range_rate_rejected_not_clamped(name: str, raw: str) -> None:
    with pytest.raises(ConfigurationError, match=name):
        TargetSettings.from_env({name: raw})


@pytest.mark.parametrize("name", ["ERROR_RATE", "TIMEOUT_RATE"])
@pytest.mark.parametrize("raw", ["0", "0.0", "1", "1.0", "0.5"])
def test_rate_boundaries_accepted(name: str, raw: str) -> None:
    settings = TargetSettings.from_env({name: raw})
    assert getattr(settings, name.lower()) == float(raw)


def test_zero_timeout_sleep_rejected() -> None:
    with pytest.raises(ConfigurationError, match=">= 1"):
        TargetSettings.from_env({"TARGET_TIMEOUT_SLEEP_MS": "0"})


def test_from_env_reads_process_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SLOW_PRICING_MS", "42")
    assert TargetSettings.from_env().slow_pricing_ms == 42


def test_log_level_is_normalised_to_upper_case() -> None:
    assert TargetSettings.from_env({"PULSEFORGE_LOG_LEVEL": "debug"}).log_level == "DEBUG"


def test_pool_size_defaults_and_rejects_zero() -> None:
    assert TargetSettings.from_env({}).db_pool_size == 5
    with pytest.raises(ConfigurationError, match=">= 1"):
        TargetSettings.from_env({"TARGET_DB_POOL_SIZE": "0"})


def test_fault_seed_is_unset_by_default_and_parsed_when_given() -> None:
    assert TargetSettings.from_env({}).fault_seed is None
    assert TargetSettings.from_env({"TARGET_FAULT_SEED": "7"}).fault_seed == 7


def test_invalid_fault_seed_rejected() -> None:
    with pytest.raises(ConfigurationError, match="TARGET_FAULT_SEED"):
        TargetSettings.from_env({"TARGET_FAULT_SEED": "later"})
