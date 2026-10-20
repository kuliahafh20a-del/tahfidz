from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_liveness() -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_versioned_api_root() -> None:
    response = client.get("/api/v1")

    assert response.status_code == 200
    assert response.json() == {"name": "YAQin API", "version": "v1"}


def test_openapi_contains_bootstrap_routes() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/health/live" in paths
    assert "/api/v1" in paths
