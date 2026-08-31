import json
import logging

from app.core.logging import (
    JsonFormatter,
    new_correlation_id,
    reset_correlation_id,
    set_correlation_id,
)


def _record(msg: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="pulseforge.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=None,
        exc_info=None,
    )


def test_formatter_emits_json_with_correlation_id() -> None:
    token = set_correlation_id("abc123")
    try:
        record = _record("thing_happened")
        record.request_id = "r-1"
        payload = json.loads(JsonFormatter().format(record))
    finally:
        reset_correlation_id(token)

    assert payload["event"] == "thing_happened"
    assert payload["component"] == "pulseforge.test"
    assert payload["correlation_id"] == "abc123"
    assert payload["request_id"] == "r-1"


def test_correlation_id_is_absent_when_unset() -> None:
    payload = json.loads(JsonFormatter().format(_record("no_context")))
    assert payload["correlation_id"] is None


def test_correlation_ids_are_unique() -> None:
    assert new_correlation_id() != new_correlation_id()
