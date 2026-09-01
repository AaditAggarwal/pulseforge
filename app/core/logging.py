"""Structured JSON logging with a correlation ID threaded through every request.

Lands in Phase 00, before anything uses it, because retrofitting correlation IDs
into async code means touching every call site and does not get done.
See OBSERVABILITY.md.
"""

from __future__ import annotations

import json
import logging
import sys
import uuid
from contextvars import ContextVar, Token
from typing import Any

_correlation_id: ContextVar[str | None] = ContextVar("pulseforge_correlation_id", default=None)

# Attributes every LogRecord carries. Anything else on a record was put there by
# us via `extra=`, and belongs in the JSON output.
_RESERVED: frozenset[str] = frozenset(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {
    "message",
    "asctime",
    "taskName",
}


def new_correlation_id() -> str:
    """Return a fresh correlation ID."""
    return uuid.uuid4().hex


def set_correlation_id(correlation_id: str) -> Token[str | None]:
    """Bind a correlation ID to the current context.

    ContextVars are per-task, so concurrent replay requests cannot see each
    other's IDs. Returns the token needed to restore the previous value.
    """
    return _correlation_id.set(correlation_id)


def reset_correlation_id(token: Token[str | None]) -> None:
    """Restore the correlation ID that was bound before `set_correlation_id`."""
    _correlation_id.reset(token)


def get_correlation_id() -> str | None:
    """Return the correlation ID bound to the current context, if any."""
    return _correlation_id.get()


class JsonFormatter(logging.Formatter):
    """Render a LogRecord as a single line of JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "event": record.getMessage(),
            "component": record.name,
            "correlation_id": get_correlation_id(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED:
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, separators=(",", ":"))


def configure_logging(level: str = "INFO") -> None:
    """Install the JSON formatter on the root logger. Idempotent."""
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


def get_logger(name: str) -> logging.Logger:
    """Return a logger. Use a dotted component name, e.g. `pulseforge.replay`."""
    return logging.getLogger(name)
