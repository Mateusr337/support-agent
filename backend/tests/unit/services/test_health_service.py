from unittest.mock import MagicMock

from app.services.health_service import HealthService


def test_check_returns_ok():
    service = HealthService()

    assert service.check() == {"status": "ok"}


def test_check_database_delegates_to_repository():
    mock_repo = MagicMock()
    service = HealthService()
    service._repository = mock_repo

    result = service.check_database()

    assert result == {"status": "ok", "database": "connected"}
    mock_repo.ping_database.assert_called_once()


def test_check_qdrant_delegates_to_repository():
    mock_repo = MagicMock()
    service = HealthService()
    service._repository = mock_repo

    result = service.check_qdrant()

    assert result == {"status": "ok", "qdrant": "connected"}
    mock_repo.ping_qdrant.assert_called_once()
