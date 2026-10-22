from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.contracts import ExpectedVersion
from app.api.pagination import CursorCodec, PaginationParams, paginate_sequence
from app.core.config import Settings, get_settings
from app.main import create_app
from app.modules.auth.dependencies import get_auth_service
from app.modules.operations.service import request_fingerprint


def test_request_id_is_echoed_and_invalid_value_is_replaced() -> None:
    supplied = "8f5e2d79-9dc1-453d-b353-626c9fc8d596"
    with TestClient(create_app()) as client:
        echoed = client.get("/api/v1", headers={"X-Request-ID": supplied})
        replaced = client.get("/api/v1", headers={"X-Request-ID": "not-a-uuid"})

    assert echoed.headers["x-request-id"] == supplied
    assert echoed.json()["request_id"] == supplied
    assert UUID(replaced.headers["x-request-id"])
    assert replaced.headers["x-request-id"] != "not-a-uuid"


def test_validation_errors_use_stable_field_error_envelope() -> None:
    application = create_app()
    application.dependency_overrides[get_auth_service] = lambda: object()
    application.dependency_overrides[get_settings] = lambda: Settings.model_validate(
        {"DATABASE_URL": "postgresql://test:test@localhost:5432/test"}
    )
    with TestClient(application) as client:
        response = client.post("/api/v1/auth/login", json={"identifier": ""})

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert "password" in response.json()["field_errors"]
    assert response.json()["request_id"] == response.headers["x-request-id"]


def test_cursor_is_opaque_scoped_and_tamper_evident() -> None:
    codec = CursorCodec("test-secret")
    first = paginate_sequence(
        [1, 2, 3],
        PaginationParams(limit=2),
        codec,
        scope="participants",
    )

    assert first.items == [1, 2]
    assert first.page.has_more is True
    assert first.page.next_cursor is not None
    second = paginate_sequence(
        [1, 2, 3],
        PaginationParams(limit=2, cursor=first.page.next_cursor),
        codec,
        scope="participants",
    )
    assert second.items == [3]
    assert second.page.has_more is False

    with pytest.raises(HTTPException):
        codec.decode(first.page.next_cursor, scope="another-scope")


def test_concurrency_and_idempotency_primitives_are_deterministic() -> None:
    command = ExpectedVersion(expected_version=7)
    assert command.expected_version == 7
    assert request_fingerprint({"b": 2, "a": 1}) == request_fingerprint({"a": 1, "b": 2})

    with pytest.raises(ValueError):
        ExpectedVersion(expected_version=0)
