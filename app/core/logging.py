"""Structured JSON logging with a correlation ID threaded through each request.

OBSERVABILITY.md requires this from the first line of code: correlation IDs
cannot be retrofitted into an async system afterwards without touching every
call site, and that does not get done. Every line carries a fixed field set --
timestamp, level, event, correlation_id, component -- and the "message" is an
event name, not a sentence, so lines can be filtered.
"""

from __future__ import annotations

import contextvars
import json
import logging
import sys
from typing import Any

# The correlation ID of the request currently being handled. Empty outside a
# request. A ContextVar is the only thing that stays correct across awaits.
correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="")


class JsonFormatter(logging.Formatter):
    """Render each log record as a single-line JSON object with fixed fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "event": record.getMessage(),
            "correlation_id": correlation_id.get(),
            "component": record.name,
        }
        context = getattr(record, "context", None)
        if isinstance(context, dict):
            payload["context"] = context
        return json.dumps(payload, separators=(",", ":"))


def configure_logging(level: str = "INFO") -> None:
    """Install the JSON formatter on the root logger. Safe to call repeatedly."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


def get_logger(component: str) -> logging.Logger:
    """Return the logger for a component; its name becomes the ``component`` field."""
    return logging.getLogger(component)
