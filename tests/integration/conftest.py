"""Shared fixtures: a seeded database and a client factory taking settings.

Every fault test needs the same service with one switch moved, so building the
app from an explicit `TargetSettings` -- rather than from process environment --
is what keeps these tests independent of each other and of the shell they run in.
"""

import asyncio
from collections.abc import Callable, Iterator
from contextlib import ExitStack
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.target.app import create_app
from app.target.config import TargetSettings
from app.target.db import connect, initialize, seed

ORDERS = 60
PRODUCTS = 20
RNG_SEED = 7


@pytest.fixture
def seeded_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "target.db"

    async def _prepare() -> None:
        conn = await connect(db_path)
        await initialize(conn)
        await seed(conn, products=PRODUCTS, orders=ORDERS, rng_seed=RNG_SEED)
        await conn.close()

    asyncio.run(_prepare())
    return db_path


@pytest.fixture
def make_client(seeded_db: Path) -> Iterator[Callable[..., TestClient]]:
    """Build a client for a service configured with the given switches."""
    with ExitStack() as stack:

        def _make(**overrides: Any) -> TestClient:
            settings = TargetSettings(db_path=seeded_db, db_pool_size=2, **overrides)
            return stack.enter_context(TestClient(create_app(settings)))

        yield _make


@pytest.fixture
def client(make_client: Callable[..., TestClient]) -> TestClient:
    """The clean service: every switch off."""
    return make_client()
