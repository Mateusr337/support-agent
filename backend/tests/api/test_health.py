from unittest.mock import MagicMock

from app.api.v1.dependencies import get_health_service
from app.main import app


def test_health_returns_ok(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_db_returns_connected(client):
    mock_service = MagicMock()
    mock_service.check_database.return_value = {
        "status": "ok",
        "database": "connected",
    }
    app.dependency_overrides[get_health_service] = lambda: mock_service

    try:
        response = client.get("/api/v1/health/db")
    finally:
        app.dependency_overrides.pop(get_health_service, None)

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}
    mock_service.check_database.assert_called_once()


def test_health_qdrant_returns_connected(client):
    mock_service = MagicMock()
    mock_service.check_qdrant.return_value = {
        "status": "ok",
        "qdrant": "connected",
    }
    app.dependency_overrides[get_health_service] = lambda: mock_service

    try:
        response = client.get("/api/v1/health/qdrant")
    finally:
        app.dependency_overrides.pop(get_health_service, None)

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "qdrant": "connected"}
    mock_service.check_qdrant.assert_called_once()


def test_health_db_returns_503_when_unavailable(client):
    mock_service = MagicMock()
    mock_service.check_database.side_effect = RuntimeError("connection refused")
    app.dependency_overrides[get_health_service] = lambda: mock_service

    try:
        response = client.get("/api/v1/health/db")
    finally:
        app.dependency_overrides.pop(get_health_service, None)

    assert response.status_code == 503
    assert response.json()["detail"] == "Database unavailable"


def test_health_qdrant_returns_503_when_unavailable(client):
    mock_service = MagicMock()
    mock_service.check_qdrant.side_effect = RuntimeError("connection refused")
    app.dependency_overrides[get_health_service] = lambda: mock_service

    try:
        response = client.get("/api/v1/health/qdrant")
    finally:
        app.dependency_overrides.pop(get_health_service, None)

    assert response.status_code == 503
    assert response.json()["detail"] == "Qdrant unavailable"
