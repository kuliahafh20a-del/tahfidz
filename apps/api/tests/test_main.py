import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.main import app, create_app

client = TestClient(app)


def test_liveness() -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_checks_database(monkeypatch: pytest.MonkeyPatch) -> None:
    class HealthyDatabase:
        async def ping(self) -> None:
            return None

    monkeypatch.setattr("app.main.get_database", lambda: HealthyDatabase())

    with TestClient(create_app()) as readiness_client:
        response = readiness_client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_readiness_hides_database_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    class UnavailableDatabase:
        async def ping(self) -> None:
            raise SQLAlchemyError("connection details must stay private")

    monkeypatch.setattr("app.main.get_database", lambda: UnavailableDatabase())

    with TestClient(create_app()) as readiness_client:
        response = readiness_client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": {"status": "not_ready"}}


def test_versioned_api_root() -> None:
    response = client.get("/api/v1")

    assert response.status_code == 200
    assert response.json() == {"name": "YAQin API", "version": "v1"}


def test_openapi_contains_bootstrap_routes() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/health/live" in paths
    assert "/health/ready" in paths
    assert "/api/v1" in paths
