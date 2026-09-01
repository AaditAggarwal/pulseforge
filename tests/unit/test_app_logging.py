"""Regression test for FM-001: structured logs dropped under uvicorn.

Uvicorn installs handlers on its own loggers and leaves the root logger bare, so
a service that only calls `get_logger` emits nothing when launched the real way.
`create_app` must install the JSON handler itself.
"""

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.core.logging import JsonFormatter
from app.target.app import create_app
from app.target.config import TargetSettings


@pytest.fixture
def bare_root_logger() -> Iterator[None]:
    """Strip the root logger the way uvicorn leaves it, then put it back."""
    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    root.handlers.clear()
    yield
    root.handlers[:] = saved_handlers
    root.setLevel(saved_level)


def test_create_app_installs_the_json_handler(bare_root_logger: None) -> None:
    create_app(TargetSettings(db_path=Path("unused.db")))
    handlers = logging.getLogger().handlers
    assert handlers, "root logger left bare: the service would log nothing under uvicorn"
    assert any(isinstance(handler.formatter, JsonFormatter) for handler in handlers)


def test_create_app_honours_the_configured_log_level(bare_root_logger: None) -> None:
    create_app(TargetSettings(db_path=Path("unused.db"), log_level="WARNING"))
    assert logging.getLogger().level == logging.WARNING
