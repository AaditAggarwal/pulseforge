"""Target-service configuration, read once at process startup.

The four fault switches are the ground truth every later phase verifies against,
so they are parsed into a frozen object at startup and never mutated afterwards.
One process serves exactly one configuration; reconfiguring means restarting.
That is deliberate. Flipping a switch inside a live process would carry warmed
caches and connection state across the baseline/candidate boundary, restoring
the confounder that runtime switching exists to remove.

The four fault names are deliberately unprefixed -- they are the documented
contract named in PROJECT_CONTEXT's V0 definition and in `.env.example`.
Operational settings that are not part of that contract carry a `TARGET_`
prefix, so a reader can tell a fault switch from a knob at a glance.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from app.core.errors import ConfigurationError

_DEFAULT_DB_PATH = Path("./data/target.db")

# What a "timeout" actually does server-side: sleep far past any sane client
# deadline. The fault is a hang, not a 504 -- a 504 would be an error, and
# ERROR_RATE already covers that case.
_DEFAULT_TIMEOUT_SLEEP_MS = 30_000

# Connections are pooled rather than shared. A single shared connection would
# serialize every query in the process, so the N+1 switch would be measured as
# queueing behind itself rather than as the cost of the extra queries -- the
# fixture would exaggerate its own fault.
_DEFAULT_DB_POOL_SIZE = 5

_TRUE = frozenset({"1", "true", "yes", "on"})
_FALSE = frozenset({"0", "false", "no", "off"})


def _raw(env: Mapping[str, str], name: str) -> str | None:
    """Return a stripped value, treating unset and empty-string as identical.

    `.env.example` ships every name with a value, so a user who blanks one out
    means "default", not "empty string".
    """
    value = env.get(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _get_bool(env: Mapping[str, str], name: str, default: bool) -> bool:
    raw = _raw(env, name)
    if raw is None:
        return default
    lowered = raw.lower()
    if lowered in _TRUE:
        return True
    if lowered in _FALSE:
        return False
    raise ConfigurationError(f"{name} must be one of {sorted(_TRUE | _FALSE)}, got {raw!r}")


def _get_int(env: Mapping[str, str], name: str, default: int, *, minimum: int = 0) -> int:
    raw = _raw(env, name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ConfigurationError(f"{name} must be an integer, got {raw!r}") from None
    if value < minimum:
        raise ConfigurationError(f"{name} must be >= {minimum}, got {value}")
    return value


def _get_optional_int(env: Mapping[str, str], name: str) -> int | None:
    """Like `_get_int`, but unset means None rather than a default value."""
    raw = _raw(env, name)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        raise ConfigurationError(f"{name} must be an integer, got {raw!r}") from None


def _get_rate(env: Mapping[str, str], name: str, default: float) -> float:
    """Parse a probability. Out-of-range is a hard error, never a silent clamp.

    Clamping 1.5 to 1.0 would let a typo produce a plausible-looking run whose
    injected fault rate is not the one the operator asked for, and every number
    downstream would be quietly wrong.
    """
    raw = _raw(env, name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        raise ConfigurationError(f"{name} must be a number, got {raw!r}") from None
    if not 0.0 <= value <= 1.0:
        raise ConfigurationError(f"{name} must be between 0.0 and 1.0 inclusive, got {value}")
    return value


@dataclass(frozen=True, slots=True)
class TargetSettings:
    """Immutable startup configuration for the target service."""

    slow_pricing_ms: int = 0
    n_plus_one: bool = False
    error_rate: float = 0.0
    timeout_rate: float = 0.0
    db_path: Path = _DEFAULT_DB_PATH
    db_pool_size: int = _DEFAULT_DB_POOL_SIZE
    timeout_sleep_ms: int = _DEFAULT_TIMEOUT_SLEEP_MS
    log_level: str = "INFO"
    fault_seed: int | None = None

    def __post_init__(self) -> None:
        # One uniform draw picks between error, timeout and neither, so the
        # configured probabilities are the observed ones exactly. That only
        # holds while they fit inside a single unit interval.
        if self.error_rate + self.timeout_rate > 1.0:
            raise ConfigurationError(
                "ERROR_RATE + TIMEOUT_RATE must not exceed 1.0, got "
                f"{self.error_rate} + {self.timeout_rate}"
            )

    @property
    def faults_enabled(self) -> bool:
        """True if any regression switch is on. Logged once at startup."""
        return bool(self.slow_pricing_ms or self.n_plus_one or self.error_rate or self.timeout_rate)

    @property
    def active_faults(self) -> dict[str, int | float | bool]:
        """The switches that are on, for the startup log line and `/__config`."""
        candidates: dict[str, int | float | bool] = {
            "SLOW_PRICING_MS": self.slow_pricing_ms,
            "N_PLUS_ONE": self.n_plus_one,
            "ERROR_RATE": self.error_rate,
            "TIMEOUT_RATE": self.timeout_rate,
        }
        return {name: value for name, value in candidates.items() if value}

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> TargetSettings:
        """Parse settings from a mapping, defaulting to the process environment.

        Raises `ConfigurationError` on any invalid value -- at startup, never
        mid-run, per the contract in `app.core.errors`.
        """
        source: Mapping[str, str] = os.environ if env is None else env
        return cls(
            slow_pricing_ms=_get_int(source, "SLOW_PRICING_MS", 0),
            n_plus_one=_get_bool(source, "N_PLUS_ONE", default=False),
            error_rate=_get_rate(source, "ERROR_RATE", 0.0),
            timeout_rate=_get_rate(source, "TIMEOUT_RATE", 0.0),
            db_path=Path(_raw(source, "TARGET_DB_PATH") or _DEFAULT_DB_PATH),
            db_pool_size=_get_int(source, "TARGET_DB_POOL_SIZE", _DEFAULT_DB_POOL_SIZE, minimum=1),
            timeout_sleep_ms=_get_int(
                source, "TARGET_TIMEOUT_SLEEP_MS", _DEFAULT_TIMEOUT_SLEEP_MS, minimum=1
            ),
            log_level=(_raw(source, "PULSEFORGE_LOG_LEVEL") or "INFO").upper(),
            fault_seed=_get_optional_int(source, "TARGET_FAULT_SEED"),
        )
