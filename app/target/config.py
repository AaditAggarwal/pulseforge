"""Regression switches for the target service, read once at startup.

A "regression" is toggled by deploying the candidate with a switch flipped:
baseline runs with everything off, the candidate flips one on, and the gate must
notice the difference. The switches change *performance*, never correctness.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

_TRUTHY = {"1", "true", "yes", "on"}


def _read_bool(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in _TRUTHY


def _read_fraction(name: str) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return 0.0
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number in [0.0, 1.0], got {raw!r}") from exc
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in [0.0, 1.0], got {value!r}")
    return value


@dataclass(frozen=True, slots=True)
class TargetConfig:
    """The three deliberate regressions, off by default (the baseline)."""

    slow_pricing: bool = False
    n_plus_one: bool = False
    error_rate: float = 0.0

    @classmethod
    def from_env(cls) -> TargetConfig:
        """Read the switches from the process environment (see ``.env.example``)."""
        return cls(
            slow_pricing=_read_bool("SLOW_PRICING"),
            n_plus_one=_read_bool("N_PLUS_ONE"),
            error_rate=_read_fraction("ERROR_RATE"),
        )
