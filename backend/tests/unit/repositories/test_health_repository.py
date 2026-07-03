from unittest.mock import MagicMock, patch

from app.repositories.health_repository import HealthRepository


@patch("app.repositories.health_repository.engine")
def test_ping_database_executes_select(mock_engine):
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    mock_engine.connect.return_value.__exit__.return_value = False

    HealthRepository().ping_database()

    mock_engine.connect.assert_called_once()
    mock_conn.execute.assert_called_once()


@patch("app.repositories.health_repository.get_qdrant_client")
def test_ping_qdrant_calls_get_collections(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    HealthRepository().ping_qdrant()

    mock_get_client.assert_called_once()
    mock_client.get_collections.assert_called_once()
