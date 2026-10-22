"""Request correlation, cache policy, and privacy-safe structured logging."""

import json
import logging
from collections.abc import Awaitable, Callable
from time import perf_counter
from uuid import UUID, uuid4

from fastapi import FastAPI, Request, Response

logger = logging.getLogger("yaqin.api")


def _request_id(value: str | None) -> UUID:
    if value is not None:
        try:
            return UUID(value)
        except ValueError:
            pass
    return uuid4()


async def request_context_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Correlate one request without logging its payload, query, or credentials."""
    correlation_id = _request_id(request.headers.get("X-Request-ID"))
    request.state.request_id = correlation_id
    started = perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = str(correlation_id)
    if request.url.path.startswith("/api/v1"):
        response.headers["Cache-Control"] = "no-store"

    route = request.scope.get("route")
    route_template = getattr(route, "path", request.url.path)
    logger.info(
        json.dumps(
            {
                "event": "http_request_completed",
                "request_id": str(correlation_id),
                "method": request.method,
                "route": route_template,
                "status_code": response.status_code,
                "duration_ms": round((perf_counter() - started) * 1000, 2),
            },
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return response


def install_request_context(application: FastAPI) -> None:
    """Install request context before routes are served."""
    application.middleware("http")(request_context_middleware)
