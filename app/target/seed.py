"""Seed the target service's database. `uv run python -m app.target.seed`.

Separate from the service so seeding is an explicit, observable step. A service
that seeds itself on startup would hide the row count behind whatever the last
process happened to do, and row count is one of the variables that determines
the latency the gate measures.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from app.core.logging import configure_logging, get_logger
from app.target.config import TargetSettings
from app.target.db import (
    DEFAULT_ORDERS,
    DEFAULT_PRODUCTS,
    DEFAULT_RNG_SEED,
    connect,
    initialize,
    row_counts,
    seed,
)

log = get_logger("pulseforge.target.seed")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed the target service database.")
    parser.add_argument("--db", type=Path, default=None, help="defaults to TARGET_DB_PATH")
    parser.add_argument("--products", type=int, default=DEFAULT_PRODUCTS)
    parser.add_argument("--orders", type=int, default=DEFAULT_ORDERS)
    parser.add_argument("--rng-seed", type=int, default=DEFAULT_RNG_SEED)
    parser.add_argument("--force", action="store_true", help="wipe and re-seed")
    return parser.parse_args(argv)


async def _run(args: argparse.Namespace) -> None:
    db_path = args.db or TargetSettings.from_env().db_path
    conn = await connect(db_path)
    try:
        await initialize(conn)
        wrote = await seed(
            conn,
            products=args.products,
            orders=args.orders,
            rng_seed=args.rng_seed,
            force=args.force,
        )
        counts = await row_counts(conn)
    finally:
        await conn.close()

    log.info(
        "seed_complete" if wrote else "seed_skipped_already_populated",
        extra={"db_path": str(db_path), "rng_seed": args.rng_seed, **counts},
    )


def main(argv: list[str] | None = None) -> None:
    configure_logging()
    asyncio.run(_run(_parse_args(argv)))


if __name__ == "__main__":
    main()
