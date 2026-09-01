"""Everything the service does differently when a regression switch is on.

Deliberately one file. The fixture's credibility rests on being able to answer
"what exactly changes when this switch flips" without reading the whole service,
because every verdict the gate ever produces is validated against these four
behaviours.

What is modelled, and what is not:

* `SLOW_PRICING_MS` is an `asyncio.sleep`, so it models added *I/O wait* -- a new
  call to a downstream pricing service, the most common real latency regression.
  It does not model a CPU-bound regression, which would also degrade concurrent
  requests by blocking the event loop. That is a genuinely different failure
  shape and would need its own switch.
* `N_PLUS_ONE` costs one indexed query per row, as an ORM lazy-load does.
* `ERROR_RATE` and `TIMEOUT_RATE` are drawn *per request in middleware*, so they
  apply uniformly to every route including `/health`. A partial fault would be
  more realistic, but it would make the expected error rate per endpoint depend
  on the workload mix, and Phase 05 needs a rate it can predict exactly.
"""

from __future__ import annotations

import asyncio
import random
from enum import StrEnum

from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.logging import get_logger
from app.target.config import TargetSettings

log = get_logger("pulseforge.target.faults")


class Fault(StrEnum):
    ERROR = "error"
    TIMEOUT = "timeout"


class FaultInjector:
    """Owns the RNG and every fault decision. One instance per process.

    `TARGET_FAULT_SEED` makes the *sequence* of draws reproducible, which under
    serial traffic means identical fault placement and makes a surprising 500
    debuggable. It does not survive concurrency: which in-flight request gets
    which draw depends on scheduling. Per-request determinism needs a stable
    request identifier from the replay engine, so it is a Phase 04 decision,
    not one to guess at here.
    """

    def __init__(self, settings: TargetSettings) -> None:
        self._settings = settings
        self._rng = random.Random(settings.fault_seed)  # noqa: S311 -- fixture, not crypto

    def draw(self) -> Fault | None:
        """One uniform draw, so P(error) and P(timeout) are exactly as configured."""
        error_rate = self._settings.error_rate
        cumulative = error_rate + self._settings.timeout_rate
        if cumulative == 0.0:
            return None
        value = self._rng.random()
        if value < error_rate:
            return Fault.ERROR
        if value < cumulative:
            return Fault.TIMEOUT
        return None

    async def slow_pricing(self) -> None:
        """Injected latency on the shared pricing path. No-op when switched off."""
        if self._settings.slow_pricing_ms:
            await asyncio.sleep(self._settings.slow_pricing_ms / 1000)


async def _send_json(send: Send, status: int, body: bytes) -> None:
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


class FaultMiddleware:
    """Raw ASGI, not `BaseHTTPMiddleware`.

    `BaseHTTPMiddleware` wraps each request in an anyio task group and buffers
    the response, adding latency and variance to every request whether or not a
    fault fires. Measurement overhead in the fault-injection layer would land
    directly in the numbers the gate compares.
    """

    def __init__(self, app: ASGIApp, injector: FaultInjector, settings: TargetSettings) -> None:
        self._app = app
        self._injector = injector
        self._settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        fault = self._injector.draw()
        if fault is None:
            await self._app(scope, receive, send)
            return

        log.warning("fault_injected", extra={"fault": str(fault), "path": scope.get("path")})
        if fault is Fault.ERROR:
            await _send_json(send, 500, b'{"detail":"injected failure"}')
            return

        # A timeout is a hang, not a status code: the client must be the thing
        # that gives up. The 504 below is only what a client patient enough to
        # wait would eventually see.
        await asyncio.sleep(self._settings.timeout_sleep_ms / 1000)
        await _send_json(send, 504, b'{"detail":"injected timeout"}')
