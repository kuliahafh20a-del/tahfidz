"""Central HTTP and validation error mapping for the public API contract."""

import json
import logging
from collections import defaultdict
from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.contracts import ErrorEnvelope, request_id

logger = logging.getLogger("yaqin.api")

DEFAULT_CODES = {
    status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
    status.HTTP_401_UNAUTHORIZED: "AUTHENTICATION_REQUIRED",
    status.HTTP_403_FORBIDDEN: "ACCESS_DENIED",
    status.HTTP_404_NOT_FOUND: "RESOURCE_NOT_FOUND",
    status.HTTP_409_CONFLICT: "INVALID_STATE_TRANSITION",
    status.HTTP_422_UNPROCESSABLE_CONTENT: "VALIDATION_ERROR",
    status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMITED",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "INTERNAL_ERROR",
    status.HTTP_503_SERVICE_UNAVAILABLE: "SERVICE_UNAVAILABLE",
}

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    code: {"model": ErrorEnvelope} for code in (400, 401, 403, 404, 409, 422, 429, 500, 503)
}


def _message(status_code: int, supplied: object | None = None) -> str:
    if isinstance(supplied, str) and supplied:
        return supplied
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "Permintaan tidak dapat diproses."


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    field_errors: dict[str, list[str]] | None = None,
    details: dict[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    payload = ErrorEnvelope(
        code=code.upper(),
        message=message,
        field_errors=field_errors or {},
        details=details or {},
        request_id=request_id(request),
    )
    return JSONResponse(
        content=payload.model_dump(mode="json"),
        status_code=status_code,
        headers=headers,
    )


async def http_exception_handler(request: Request, error: HTTPException) -> JSONResponse:
    """Translate FastAPI HTTP errors without exposing internal details."""
    detail: dict[str, Any] = error.detail if isinstance(error.detail, dict) else {}
    supplied_code = detail.get("code")
    code = (
        str(supplied_code).upper()
        if supplied_code
        else DEFAULT_CODES.get(error.status_code, "REQUEST_FAILED")
    )
    field_errors = detail.get("field_errors")
    details = detail.get("details")
    return _error_response(
        request,
        status_code=error.status_code,
        code=code,
        message=_message(error.status_code, detail.get("message")),
        field_errors=field_errors if isinstance(field_errors, dict) else None,
        details=details if isinstance(details, dict) else None,
        headers=error.headers,
    )


async def validation_exception_handler(
    request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    """Group Pydantic errors by public request field."""
    grouped: defaultdict[str, list[str]] = defaultdict(list)
    for item in error.errors():
        location = [
            str(part) for part in item.get("loc", ()) if part not in {"body", "query", "path"}
        ]
        field = ".".join(location) or "request"
        grouped[field].append(str(item.get("msg", "Nilai tidak valid.")))
    return _error_response(
        request,
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="VALIDATION_ERROR",
        message="Periksa kembali field yang belum valid.",
        field_errors=dict(grouped),
    )


async def unexpected_exception_handler(request: Request, error: Exception) -> JSONResponse:
    """Return a generic response while leaving exception details to server logs."""
    logger.error(
        json.dumps(
            {
                "error_type": type(error).__name__,
                "event": "http_request_failed",
                "request_id": str(request_id(request)),
            },
            separators=(",", ":"),
            sort_keys=True,
        ),
        exc_info=(type(error), error, error.__traceback__),
    )
    return _error_response(
        request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_ERROR",
        message="Terjadi kesalahan internal. Gunakan request ID saat menghubungi dukungan.",
    )


def install_error_handlers(application: FastAPI) -> None:
    """Register all shared exception handlers in one place."""
    application.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
    application.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    application.add_exception_handler(Exception, unexpected_exception_handler)
