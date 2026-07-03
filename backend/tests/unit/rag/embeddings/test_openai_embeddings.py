import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.rag.embeddings.factory import get_embedding_provider
from app.rag.embeddings.openai import OpenAIEmbeddingProvider


def _provider_with_mock_client(mock_client: MagicMock) -> OpenAIEmbeddingProvider:
    provider = OpenAIEmbeddingProvider.__new__(OpenAIEmbeddingProvider)
    provider._client = mock_client
    provider._model = "text-embedding-3-small"
    return provider


def test_init_raises_for_unsupported_model():
    with pytest.raises(ValueError, match="Unsupported embedding model"):
        OpenAIEmbeddingProvider(api_key="test-key", model="unknown-model")


def test_dimension_for_text_embedding_3_small():
    provider = OpenAIEmbeddingProvider(
        api_key="test-key",
        model="text-embedding-3-small",
    )
    assert provider.model == "text-embedding-3-small"
    assert provider.dimension == 1536


def test_embed_returns_empty_list_for_empty_input():
    provider = _provider_with_mock_client(MagicMock())
    result = asyncio.run(provider.embed([]))
    assert result == []


def test_embed_returns_vectors_using_mock_client():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [
        MagicMock(embedding=[0.1, 0.2]),
        MagicMock(embedding=[0.3, 0.4]),
    ]
    mock_response.usage = MagicMock(total_tokens=42)
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)

    provider = _provider_with_mock_client(mock_client)
    result = asyncio.run(provider.embed(["first chunk", "second chunk"]))

    assert result == [[0.1, 0.2], [0.3, 0.4]]
    mock_client.embeddings.create.assert_awaited_once_with(
        model="text-embedding-3-small",
        input=["first chunk", "second chunk"],
    )


@patch("app.rag.embeddings.factory.settings")
@patch("app.rag.embeddings.factory.OpenAIEmbeddingProvider")
def test_get_embedding_provider_returns_openai(mock_provider_class, mock_settings):
    mock_settings.embedding_provider = "openai"
    mock_settings.openai_api_key = "test-key"
    mock_settings.embedding_model = "text-embedding-3-small"
    mock_provider_class.return_value = MagicMock()

    provider = get_embedding_provider()

    mock_provider_class.assert_called_once_with(
        api_key="test-key",
        model="text-embedding-3-small",
    )
    assert provider is mock_provider_class.return_value


@patch("app.rag.embeddings.factory.settings")
def test_get_embedding_provider_raises_without_api_key(mock_settings):
    mock_settings.embedding_provider = "openai"
    mock_settings.openai_api_key = None

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        get_embedding_provider()


@patch("app.rag.embeddings.factory.settings")
def test_get_embedding_provider_raises_for_unknown_provider(mock_settings):
    mock_settings.embedding_provider = "unknown"

    with pytest.raises(ValueError, match="Unsupported embedding provider"):
        get_embedding_provider()
