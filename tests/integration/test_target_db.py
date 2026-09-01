"""Schema and seed behaviour against a real SQLite file.

Integration rather than unit: the properties that matter here -- determinism of
the seed, presence of the foreign-key index, idempotence -- are properties of
the database, not of Python objects, and a fake would assert nothing.
"""

from pathlib import Path

import aiosqlite
import pytest

from app.target.db import (
    connect,
    initialize,
    row_counts,
    seed,
)
from app.target.seed import main as seed_main


@pytest.fixture
async def conn(tmp_path: Path):
    connection = await connect(tmp_path / "target.db")
    await initialize(connection)
    yield connection
    await connection.close()


async def _fingerprint(connection: aiosqlite.Connection) -> list[tuple[object, ...]]:
    async with connection.execute(
        "SELECT o.id, o.customer_id, o.status, o.created_at, o.total_cents,"
        "       i.product_id, i.quantity, i.unit_price_cents "
        "FROM orders o JOIN order_items i ON i.order_id = o.id ORDER BY o.id, i.id"
    ) as cursor:
        return [tuple(row) for row in await cursor.fetchall()]


async def test_initialize_is_idempotent(conn: aiosqlite.Connection) -> None:
    await initialize(conn)
    assert await row_counts(conn) == {"products": 0, "orders": 0, "order_items": 0}


async def test_order_items_foreign_key_is_indexed(conn: aiosqlite.Connection) -> None:
    """The N+1 fault must hit an index, as a real ORM lazy-load would."""
    async with conn.execute("PRAGMA index_list('order_items')") as cursor:
        names = {row["name"] for row in await cursor.fetchall()}
    assert "idx_order_items_order" in names


async def test_seed_populates_all_three_tables(conn: aiosqlite.Connection) -> None:
    assert await seed(conn, products=20, orders=50) is True
    counts = await row_counts(conn)
    assert counts["products"] == 20
    assert counts["orders"] == 50
    assert 50 <= counts["order_items"] <= 50 * 6


async def test_seed_is_deterministic_for_a_given_rng_seed(tmp_path: Path) -> None:
    fingerprints = []
    for name in ("a.db", "b.db"):
        connection = await connect(tmp_path / name)
        await initialize(connection)
        await seed(connection, products=20, orders=50, rng_seed=7)
        fingerprints.append(await _fingerprint(connection))
        await connection.close()
    assert fingerprints[0] == fingerprints[1]


async def test_different_rng_seeds_produce_different_data(tmp_path: Path) -> None:
    fingerprints = []
    for name, rng_seed in (("a.db", 7), ("b.db", 8)):
        connection = await connect(tmp_path / name)
        await initialize(connection)
        await seed(connection, products=20, orders=50, rng_seed=rng_seed)
        fingerprints.append(await _fingerprint(connection))
        await connection.close()
    assert fingerprints[0] != fingerprints[1]


async def test_seed_skips_an_already_populated_database(conn: aiosqlite.Connection) -> None:
    await seed(conn, products=20, orders=50, rng_seed=7)
    before = await _fingerprint(conn)
    assert await seed(conn, products=20, orders=99, rng_seed=8) is False
    assert await _fingerprint(conn) == before


async def test_force_rewipes_and_reseeds(conn: aiosqlite.Connection) -> None:
    await seed(conn, products=20, orders=50, rng_seed=7)
    assert await seed(conn, products=20, orders=50, rng_seed=8, force=True) is True
    assert (await row_counts(conn))["orders"] == 50


async def test_order_total_matches_the_sum_of_its_items(conn: aiosqlite.Connection) -> None:
    await seed(conn, products=20, orders=50)
    async with conn.execute(
        "SELECT o.id FROM orders o JOIN order_items i ON i.order_id = o.id "
        "GROUP BY o.id HAVING o.total_cents != SUM(i.quantity * i.unit_price_cents)"
    ) as cursor:
        assert await cursor.fetchall() == []


async def test_every_order_has_at_least_one_item(conn: aiosqlite.Connection) -> None:
    await seed(conn, products=20, orders=50)
    async with conn.execute(
        "SELECT COUNT(*) FROM orders o WHERE NOT EXISTS "
        "(SELECT 1 FROM order_items i WHERE i.order_id = o.id)"
    ) as cursor:
        row = await cursor.fetchone()
    assert row is not None and row[0] == 0


def test_seed_cli_creates_and_populates_a_database(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "target.db"
    seed_main(["--db", str(db_path), "--products", "10", "--orders", "20"])
    assert db_path.exists()
