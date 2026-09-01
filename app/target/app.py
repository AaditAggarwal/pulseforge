"""The target service. Five endpoints, four distinct cost profiles.

| Route                 | Profile                                        |
|-----------------------|------------------------------------------------|
| `GET /health`         | cheap: no database, constant work              |
| `GET /pricing/quote`  | one indexed row read plus a pure computation   |
| `GET /orders/{id}`    | two indexed reads, fixed size                  |
| `GET /orders`         | variable-size collection, cost scales with N   |
| `POST /orders`        | write, multi-statement transaction             |

No fault injection in this module yet -- that lands next, so the clean profiles
above can be measured before anything perturbs them.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, cast

import aiosqlite
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.core.logging import configure_logging, get_logger
from app.target import pricing
from app.target.config import TargetSettings
from app.target.db import ConnectionPool
from app.target.faults import FaultInjector, FaultMiddleware

log = get_logger("pulseforge.target")

MAX_PAGE_SIZE = 200


class OrderItem(BaseModel):
    product_id: int
    quantity: int
    unit_price_cents: int


class Order(BaseModel):
    id: int
    customer_id: int
    status: str
    created_at: str
    total_cents: int
    items: list[OrderItem]


class QuoteResponse(BaseModel):
    product_id: int
    quantity: int
    unit_price_cents: int
    discount_bps: int
    total_cents: int


class NewOrderItem(BaseModel):
    product_id: int
    quantity: int = Field(ge=1, le=100)


class NewOrder(BaseModel):
    customer_id: int = Field(ge=1)
    items: list[NewOrderItem] = Field(min_length=1, max_length=20)


def get_pool(request: Request) -> ConnectionPool:
    # `app.state` is untyped by design in Starlette; this is the one place the
    # cast happens, so nothing downstream handles an `Any`.
    return cast(ConnectionPool, request.app.state.pool)


Pool = Annotated[ConnectionPool, Depends(get_pool)]


def _row_to_item(row: aiosqlite.Row) -> OrderItem:
    return OrderItem(
        product_id=row["product_id"],
        quantity=row["quantity"],
        unit_price_cents=row["unit_price_cents"],
    )


async def _fetch_items_n_plus_one(
    conn: aiosqlite.Connection, order_ids: list[int]
) -> dict[int, list[OrderItem]]:
    """One query per order, exactly as an ORM lazy-load would issue them.

    The regressed path. Same rows, same response bytes -- only the number of
    round trips differs, which is what makes this a *performance* regression
    that no correctness test can catch.
    """
    items: dict[int, list[OrderItem]] = {}
    for order_id in order_ids:
        async with conn.execute(
            "SELECT product_id, quantity, unit_price_cents "
            "FROM order_items WHERE order_id = ? ORDER BY id",
            (order_id,),
        ) as cursor:
            items[order_id] = [_row_to_item(row) for row in await cursor.fetchall()]
    return items


async def _fetch_items(
    conn: aiosqlite.Connection, order_ids: list[int], *, n_plus_one: bool = False
) -> dict[int, list[OrderItem]]:
    """Fetch items for every order in one query -- the non-regressed path."""
    if not order_ids:
        return {}
    if n_plus_one:
        return await _fetch_items_n_plus_one(conn, order_ids)
    placeholders = ",".join("?" * len(order_ids))
    items: dict[int, list[OrderItem]] = {order_id: [] for order_id in order_ids}
    async with conn.execute(
        "SELECT order_id, product_id, quantity, unit_price_cents "  # noqa: S608 -- placeholders only
        f"FROM order_items WHERE order_id IN ({placeholders}) ORDER BY id",
        order_ids,
    ) as cursor:
        for row in await cursor.fetchall():
            items[row["order_id"]].append(_row_to_item(row))
    return items


def _to_order(row: aiosqlite.Row, items: list[OrderItem]) -> Order:
    return Order(
        id=row["id"],
        customer_id=row["customer_id"],
        status=row["status"],
        created_at=row["created_at"],
        total_cents=row["total_cents"],
        items=items,
    )


def create_app(settings: TargetSettings | None = None) -> FastAPI:
    """Build the app. Settings are read once here and never mutated after."""
    resolved = TargetSettings.from_env() if settings is None else settings

    # Uvicorn installs handlers on its own loggers and leaves the root logger
    # bare, so without this the service's structured logs are silently dropped
    # when it runs under `make run`. Found by running it, not by reading it.
    configure_logging(resolved.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        pool = ConnectionPool(resolved.db_path, resolved.db_pool_size)
        await pool.start()
        app.state.pool = pool
        log.info(
            "target_service_started",
            extra={
                "db_path": str(resolved.db_path),
                "pool_size": resolved.db_pool_size,
                "faults": resolved.active_faults or None,
            },
        )
        try:
            yield
        finally:
            await pool.close()

    app = FastAPI(title="PulseForge target service", lifespan=lifespan)
    app.state.settings = resolved

    injector = FaultInjector(resolved)
    app.add_middleware(FaultMiddleware, injector=injector, settings=resolved)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/pricing/quote")
    async def pricing_quote(
        pool: Pool,
        product_id: Annotated[int, Query(ge=1)],
        quantity: Annotated[int, Query(ge=1, le=100)],
    ) -> QuoteResponse:
        async with (
            pool.acquire() as conn,
            conn.execute("SELECT price_cents FROM products WHERE id = ?", (product_id,)) as cursor,
        ):
            row = await cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="product not found")
        await injector.slow_pricing()
        result = pricing.quote(row["price_cents"], quantity)
        return QuoteResponse(
            product_id=product_id,
            quantity=result.quantity,
            unit_price_cents=result.unit_price_cents,
            discount_bps=result.discount_bps,
            total_cents=result.total_cents,
        )

    @app.get("/orders/{order_id}")
    async def get_order(pool: Pool, order_id: int) -> Order:
        async with pool.acquire() as conn:
            async with conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as cursor:
                row = await cursor.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="order not found")
            items = await _fetch_items(conn, [order_id])
        return _to_order(row, items[order_id])

    @app.get("/orders")
    async def list_orders(
        pool: Pool,
        limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> list[Order]:
        async with pool.acquire() as conn:
            async with conn.execute(
                "SELECT * FROM orders ORDER BY id LIMIT ? OFFSET ?", (limit, offset)
            ) as cursor:
                rows = await cursor.fetchall()
            items = await _fetch_items(
                conn, [row["id"] for row in rows], n_plus_one=resolved.n_plus_one
            )
        return [_to_order(row, items[row["id"]]) for row in rows]

    @app.post("/orders", status_code=201)
    async def create_order(pool: Pool, payload: NewOrder) -> Order:
        async with pool.acquire() as conn:
            priced: list[tuple[int, int, int]] = []
            total = 0
            for item in payload.items:
                async with conn.execute(
                    "SELECT price_cents FROM products WHERE id = ?", (item.product_id,)
                ) as cursor:
                    product = await cursor.fetchone()
                if product is None:
                    raise HTTPException(
                        status_code=404, detail=f"product {item.product_id} not found"
                    )
                await injector.slow_pricing()
                result = pricing.quote(product["price_cents"], item.quantity)
                total += result.total_cents
                priced.append((item.product_id, item.quantity, result.unit_price_cents))

            cursor = await conn.execute(
                "INSERT INTO orders (customer_id, status, created_at, total_cents) "
                "VALUES (?, 'pending', datetime('now'), ?)",
                (payload.customer_id, total),
            )
            order_id = cast(int, cursor.lastrowid)
            await conn.executemany(
                "INSERT INTO order_items (order_id, product_id, quantity, unit_price_cents) "
                "VALUES (?, ?, ?, ?)",
                [(order_id, *row) for row in priced],
            )
            await conn.commit()
            async with conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as c:
                row = cast(aiosqlite.Row, await c.fetchone())
            items = await _fetch_items(conn, [order_id])
        return _to_order(row, items[order_id])

    return app
