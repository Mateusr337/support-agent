import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.llm.base import Message
from app.core.llm.factory import get_llm_provider
from app.core.llm.openai import OpenAILLMProvider


@patch("app.core.llm.openai.AsyncOpenAI")
def test_openai_provider_returns_assistant_content(mock_async_openai):
    mock_client = MagicMock()
    mock_async_openai.return_value = mock_client

    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Reset the printer."))]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    provider = OpenAILLMProvider(api_key="test-key", model="gpt-4o-mini")
    result = asyncio.run(
        provider.chat(
            [Message(role="user", content="How do I reset my printer?")],
            temperature=0.1,
        )
    )

    assert result == "Reset the printer."
    mock_async_openai.assert_called_once_with(api_key="test-key")
    mock_client.chat.completions.create.assert_awaited_once_with(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "How do I reset my printer?"}],
        temperature=0.1,
    )


@patch("app.core.llm.openai.AsyncOpenAI")
def test_openai_provider_raises_when_content_is_empty(mock_async_openai):
    mock_client = MagicMock()
    mock_async_openai.return_value = mock_client

    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=None))]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    provider = OpenAILLMProvider(api_key="test-key", model="gpt-4o-mini")

    with pytest.raises(RuntimeError, match="empty response"):
        asyncio.run(provider.chat([Message(role="user", content="Hello")]))


@patch("app.core.llm.factory.settings")
@patch("app.core.llm.factory.OpenAILLMProvider")
def test_get_llm_provider_returns_openai(mock_provider_class, mock_settings):
    mock_settings.llm_provider = "openai"
    mock_settings.openai_api_key = "test-key"
    mock_settings.llm_model = "gpt-4o-mini"
    mock_provider_class.return_value = MagicMock()

    provider = get_llm_provider()

    mock_provider_class.assert_called_once_with(
        api_key="test-key",
        model="gpt-4o-mini",
    )
    assert provider is mock_provider_class.return_value


@patch("app.core.llm.factory.settings")
def test_get_llm_provider_raises_without_api_key(mock_settings):
    mock_settings.llm_provider = "openai"
    mock_settings.openai_api_key = None

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        get_llm_provider()


@patch("app.core.llm.factory.settings")
def test_get_llm_provider_raises_for_unknown_provider(mock_settings):
    mock_settings.llm_provider = "unknown"

    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        get_llm_provider()
