"""Shared request and response schemas for the versioned HTTP API."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import Header, Request
from pydantic import BaseModel, Field


class SuccessEnvelope[T](BaseModel):
    """Stable wrapper for resources, commands, and collections."""

    data: T
    version: int | None = None
    request_id: UUID


class ErrorEnvelope(BaseModel):
    """Safe and actionable error representation shared by every endpoint."""

    code: str
    message: str
    field_errors: dict[str, list[str]] = Field(default_factory=dict)
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: UUID


class ExpectedVersion(BaseModel):
    """Optimistic concurrency input for mutable resources."""

    expected_version: int = Field(ge=1)


IdempotencyKey = Annotated[
    UUID,
    Header(
        alias="Idempotency-Key",
        description="UUID unique to one logical command and payload.",
    ),
]


def request_id(request: Request) -> UUID:
    """Read the validated request identifier assigned by middleware."""
    value = getattr(request.state, "request_id", None)
    if not isinstance(value, UUID):
        raise RuntimeError("request ID middleware is not installed")
    return value


def success[T](
    request: Request,
    data: T,
    *,
    version: int | None = None,
) -> SuccessEnvelope[T]:
    """Build a success envelope using the current request context."""
    return SuccessEnvelope(data=data, version=version, request_id=request_id(request))
