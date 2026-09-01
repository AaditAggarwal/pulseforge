"""SQLite schema and deterministic seed data for the target service.

Real I/O on purpose. An in-memory dict would make the `N_PLUS_ONE` switch nearly
free and the fixture would stop being ground truth for anything the gate claims
to detect.

Two choices here shape how hard the injected N+1 is to detect, and both are
deliberate:

* `order_items(order_id)` is indexed. A real ORM lazy-load hits an indexed
  foreign key, so the injected fault costs one cheap query per row rather than
  one table scan per row. Dropping the index would make the fault enormous and
  the gate's job trivial -- a strawman regression proves nothing about
  sensitivity.
* Seed data is generated from a fixed RNG seed. Phase 04 replays a recorded
  corpus; if the rows behind an endpoint differed between baseline and candidate
  runs, the workload would no longer be byte-identical in effect, whatever the
  request bytes said.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id           INTEGER PRIMARY KEY,
    sku          TEXT    NOT NULL UNIQUE,
    name         TEXT    NOT NULL,
    category     TEXT    NOT NULL,
    price_cents  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id           INTEGER PRIMARY KEY,
    customer_id  INTEGER NOT NULL,
    status       TEXT    NOT NULL,
    created_at   TEXT    NOT NULL,
    total_cents  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);

CREATE TABLE IF NOT EXISTS order_items (
    id                INTEGER PRIMARY KEY,
    order_id          INTEGER NOT NULL REFERENCES orders(id),
    product_id        INTEGER NOT NULL REFERENCES products(id),
    quantity          INTEGER NOT NULL,
    unit_price_cents  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
"""

DEFAULT_PRODUCTS = 200
DEFAULT_ORDERS = 2_000
DEFAULT_RNG_SEED = 20260101

_EPOCH = datetime(2026, 1, 1, tzinfo=UTC)
_CATEGORIES = ("audio", "cable", "display", "keyboard", "storage")
_STATUSES = ("pending", "paid", "shipped", "delivered", "refunded")
_MAX_ITEMS_PER_ORDER = 6


async def connect(db_path: Path) -> aiosqlite.Connection:
    """Open a connection with the pragmas the fixture depends on.

    WAL matters: under the default rollback journal a single writer blocks every
    reader, so the write endpoint's latency would be dominated by lock
    contention -- an artifact of database configuration rather than of the code
    the gate is supposed to be judging.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA synchronous=NORMAL")
    await conn.execute("PRAGMA foreign_keys=ON")
    return conn


async def initialize(conn: aiosqlite.Connection) -> None:
    """Create the schema. Idempotent."""
    await conn.executescript(SCHEMA)
    await conn.commit()


async def row_counts(conn: aiosqlite.Connection) -> dict[str, int]:
    """Row count per table, for the seed CLI and for tests."""
    counts: dict[str, int] = {}
    for table in ("products", "orders", "order_items"):
        async with conn.execute(f"SELECT COUNT(*) FROM {table}") as cursor:  # noqa: S608
            row = await cursor.fetchone()
        counts[table] = 0 if row is None else int(row[0])
    return counts


async def seed(
    conn: aiosqlite.Connection,
    *,
    products: int = DEFAULT_PRODUCTS,
    orders: int = DEFAULT_ORDERS,
    rng_seed: int = DEFAULT_RNG_SEED,
    force: bool = False,
) -> bool:
    """Populate the database deterministically. Returns False if already seeded.

    Re-seeding with the same `rng_seed` produces byte-identical rows, so a
    corpus recorded against one seeded database stays valid against another.
    """
    counts = await row_counts(conn)
    if any(counts.values()):
        if not force:
            return False
        await conn.executescript(
            "DELETE FROM order_items; DELETE FROM orders; DELETE FROM products;"
        )

    rng = random.Random(rng_seed)  # noqa: S311 -- fixture data, not a security context

    product_rows = [
        (
            pid,
            f"SKU-{pid:05d}",
            f"{_CATEGORIES[pid % len(_CATEGORIES)]} unit {pid}",
            _CATEGORIES[pid % len(_CATEGORIES)],
            rng.randrange(500, 50_000),
        )
        for pid in range(1, products + 1)
    ]
    prices = {row[0]: row[4] for row in product_rows}

    order_rows: list[tuple[int, int, str, str, int]] = []
    item_rows: list[tuple[int, int, int, int, int]] = []
    item_id = 0
    for order_id in range(1, orders + 1):
        total = 0
        for _ in range(rng.randint(1, _MAX_ITEMS_PER_ORDER)):
            item_id += 1
            product_id = rng.randint(1, products)
            quantity = rng.randint(1, 4)
            unit_price = prices[product_id]
            total += quantity * unit_price
            item_rows.append((item_id, order_id, product_id, quantity, unit_price))
        order_rows.append(
            (
                order_id,
                rng.randint(1, max(1, orders // 4)),
                _STATUSES[rng.randrange(len(_STATUSES))],
                (_EPOCH + timedelta(minutes=7 * order_id)).isoformat(),
                total,
            )
        )

    await conn.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?)", product_rows)
    await conn.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", order_rows)
    await conn.executemany("INSERT INTO order_items VALUES (?, ?, ?, ?, ?)", item_rows)
    await conn.commit()
    return True


class ConnectionPool:
    """A fixed-size pool of open connections, checked out per request.

    Not an abstraction over databases -- it is the mechanism a real service uses,
    and the fixture needs it for an honest reason. One shared connection would
    serialize every query in the process, so a request running the injected N+1
    would block unrelated requests and the measured regression would be mostly
    queueing. Opening a connection per request instead would add fixed setup cost
    to every endpoint, inflating the cheap ones and shrinking the visible
    difference between them.
    """

    def __init__(self, db_path: Path, size: int) -> None:
        self._db_path = db_path
        self._size = size
        self._free: asyncio.Queue[aiosqlite.Connection] = asyncio.Queue()
        self._open: list[aiosqlite.Connection] = []

    async def start(self) -> None:
        """Open every connection up front, so no request pays connect cost."""
        for _ in range(self._size):
            conn = await connect(self._db_path)
            self._open.append(conn)
            self._free.put_nowait(conn)

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[aiosqlite.Connection]:
        """Check a connection out, blocking if all are busy."""
        conn = await self._free.get()
        try:
            yield conn
        finally:
            self._free.put_nowait(conn)

    async def close(self) -> None:
        for conn in self._open:
            await conn.close()
        self._open.clear()
