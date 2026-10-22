"""Opaque cursor pagination and explicit query-filter validation."""

import base64
import hashlib
import hmac
import json
from collections.abc import Sequence
from typing import Annotated, Any

from fastapi import HTTPException, Query, Request, status
from pydantic import BaseModel


class PageMetadata(BaseModel):
    next_cursor: str | None
    has_more: bool


class CursorPage[T](BaseModel):
    items: list[T]
    page: PageMetadata


class PaginationParams:
    """Validated pagination query parameters shared by list endpoints."""

    def __init__(
        self,
        limit: Annotated[int, Query(ge=1, le=100)] = 25,
        cursor: Annotated[str | None, Query(min_length=16, max_length=2048)] = None,
    ) -> None:
        self.limit = limit
        self.cursor = cursor


class CursorCodec:
    """Sign server-issued cursor payloads so clients cannot alter position or scope."""

    def __init__(self, secret: str) -> None:
        self.secret = secret.encode()

    def encode(self, *, offset: int, scope: str) -> str:
        payload = json.dumps(
            {"offset": offset, "scope": scope, "v": 1},
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        signature = hmac.new(self.secret, payload, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(payload + b"." + signature).decode().rstrip("=")

    def decode(self, cursor: str, *, scope: str) -> int:
        try:
            padding = "=" * (-len(cursor) % 4)
            packed = base64.urlsafe_b64decode(cursor + padding)
            payload, signature = packed.rsplit(b".", 1)
            expected = hmac.new(self.secret, payload, hashlib.sha256).digest()
            if not hmac.compare_digest(signature, expected):
                raise ValueError
            decoded: dict[str, Any] = json.loads(payload)
            offset = decoded["offset"]
            if decoded != {"offset": offset, "scope": scope, "v": 1}:
                raise ValueError
            if not isinstance(offset, int) or offset < 0:
                raise ValueError
            return offset
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_CURSOR",
                    "message": "Cursor tidak valid atau tidak sesuai dengan filter aktif.",
                    "field_errors": {"cursor": ["Gunakan cursor yang diterbitkan server."]},
                },
            ) from error


def require_query_allowlist(request: Request, allowed: set[str]) -> None:
    """Reject misspelled or unsupported filters instead of silently ignoring them."""
    unknown = sorted(set(request.query_params.keys()) - allowed)
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "VALIDATION_ERROR",
                "message": "Query memuat filter yang tidak didukung.",
                "field_errors": {
                    field: ["Filter tidak diizinkan untuk endpoint ini."] for field in unknown
                },
            },
        )


def paginate_sequence[T](
    items: Sequence[T],
    params: PaginationParams,
    codec: CursorCodec,
    *,
    scope: str,
) -> CursorPage[T]:
    """Create a stable page from an already scoped and ordered sequence."""
    offset = codec.decode(params.cursor, scope=scope) if params.cursor else 0
    page_items = list(items[offset : offset + params.limit])
    next_offset = offset + len(page_items)
    has_more = next_offset < len(items)
    return CursorPage(
        items=page_items,
        page=PageMetadata(
            next_cursor=codec.encode(offset=next_offset, scope=scope) if has_more else None,
            has_more=has_more,
        ),
    )
