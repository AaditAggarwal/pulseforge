"""The Phase 01 target service: a small FastAPI app under test.

This service is a *subject*, not part of PulseForge (ARCHITECTURE.md). Its one
unusual property is a set of deliberate, switchable regressions used as ground
truth for the gate:

    SLOW_PRICING  adds latency to the /pricing path
    N_PLUS_ONE    turns one batched query on /orders into one-query-per-row
    ERROR_RATE    fails a deterministic fraction of requests with HTTP 500

Baseline runs with the switches off; the candidate flips one on; the gate must
notice. The switches change performance, never the business result.
"""

from __future__ import annotations

import asyncio
import uuid

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.core.logging import configure_logging, correlation_id, get_logger
from app.target import store
from app.target.config import TargetConfig

log = get_logger("app.target")

# Latency added to the pricing path when SLOW_PRICING is on. Large relative to
# the sub-millisecond baseline so it lands as an unambiguous p95 regression.
SLOW_PRICING_DELAY_S = 0.05

CORRELATION_HEADER = "X-Correlation-ID"


class DeterministicErrorInjector:
    """Fail an evenly spaced ``rate`` fraction of calls, deterministically.

    Deterministic rather than random so a replay is reproducible: the same
    sequence of requests fails on the same ordinals every run (R7's spirit).
    """

    def __init__(self, rate: float) -> None:
        self._rate = rate
        self._count = 0

    def should_fail(self) -> bool:
        if self._rate <= 0.0:
            return False
        n = self._count
        self._count = n + 1
        # Fires when the running total crosses the next 1/rate boundary.
        return int((n + 1) * self._rate) > int(n * self._rate)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Assign a correlation ID to every request and inject faults per config.

    ``/health`` is never failed: it is the liveness probe, and an error-rate
    regression on business endpoints should not take liveness down with it.
    """

    def __init__(self, app: ASGIApp, injector: DeterministicErrorInjector) -> None:
        super().__init__(app)
        self._injector = injector

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        cid = request.headers.get(CORRELATION_HEADER) or uuid.uuid4().hex
        token = correlation_id.set(cid)
        try:
            if request.url.path != "/health" and self._injector.should_fail():
                log.warning("request_failed_injected")
                response: Response = JSONResponse({"detail": "injected failure"}, status_code=500)
            else:
                response = await call_next(request)
            response.headers[CORRELATION_HEADER] = cid
            return response
        finally:
            correlation_id.reset(token)


def _price_cents(sku: str) -> int:
    """A cheap, process-independent price so baseline and candidate agree."""
    return sum(ord(c) for c in sku) * 10


def create_app(config: TargetConfig | None = None) -> FastAPI:
    """Build the target service. Reads switches from the environment if unset."""
    cfg = config if config is not None else TargetConfig.from_env()
    configure_logging()
    log.info("target_service_created")

    app = FastAPI(title="PulseForge Target Service", version="0.1.0")
    app.add_middleware(ObservabilityMiddleware, injector=DeterministicErrorInjector(cfg.error_rate))

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/pricing/{sku}")
    async def pricing(sku: str) -> dict[str, object]:
        price = _price_cents(sku)
        if cfg.slow_pricing:
            # Models a slow pricing path (uncached call, heavy recompute). The
            # gate should catch this as a p95 regression on /pricing.
            await asyncio.sleep(SLOW_PRICING_DELAY_S)
        return {"sku": sku, "price_cents": price}

    @app.get("/orders")
    async def orders() -> dict[str, object]:
        rows = await store.fetch_orders()
        if cfg.n_plus_one:
            items = {o.order_id: await store.fetch_items_for(o.order_id) for o in rows}
        else:
            items = await store.fetch_items_batch([o.order_id for o in rows])
        payload = [
            {
                "order_id": o.order_id,
                "customer": o.customer,
                "line_items": len(items[o.order_id]),
                "total_cents": sum(li.quantity * li.unit_price_cents for li in items[o.order_id]),
            }
            for o in rows
        ]
        return {"count": len(payload), "orders": payload}

    return app
