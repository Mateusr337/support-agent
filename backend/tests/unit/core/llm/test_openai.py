import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.llm.base import Message
from app.core.llm.factory import get_llm_provider
from app.core.llm.openai import OpenAILLMProvider


def _provider_with_mock_client(mock_client: MagicMock) -> OpenAILLMProvider:
    provider = OpenAILLMProvider.__new__(OpenAILLMProvider)
    provider._client = mock_client
    provider._model = "gpt-4o-mini"
    return provider


def test_audit_info_skips_when_context_is_incomplete():
    provider = _provider_with_mock_client(MagicMock())
    audit_log = MagicMock()

    provider._audit_info(
        audit_log,
        session_id=None,
        user_id=1,
        turn_id=uuid4(),
        type="agent_request",
        message="LLM request",
        data={},
    )

    audit_log.info.assert_not_called()


def test_audit_info_writes_log_when_context_is_complete():
    provider = _provider_with_mock_client(MagicMock())
    audit_log = MagicMock()
    session_id = uuid4()
    turn_id = uuid4()

    provider._audit_info(
        audit_log,
        session_id=session_id,
        user_id=1,
        turn_id=turn_id,
        type="token_usage",
        message="LLM token usage",
        data={"total_tokens": 15},
    )

    audit_log.info.assert_called_once_with(
        session_id=session_id,
        user_id=1,
        turn_id=turn_id,
        type="token_usage",
        message="LLM token usage",
        data={"total_tokens": 15},
    )


def test_chat_returns_assistant_content_using_mock_client():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Reset the printer."))]
    mock_response.usage = None
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    provider = _provider_with_mock_client(mock_client)
    result = asyncio.run(
        provider.chat(
            [Message(role="user", content="How do I reset my printer?")],
            temperature=0.1,
        )
    )

    assert result == "Reset the printer."
    mock_client.chat.completions.create.assert_awaited_once_with(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "How do I reset my printer?"}],
        temperature=0.1,
    )


def test_chat_logs_audit_entries_when_context_is_provided():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Done"))]
    mock_response.usage = MagicMock(
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
    )
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    audit_log = MagicMock()
    session_id = uuid4()
    turn_id = uuid4()
    provider = _provider_with_mock_client(mock_client)

    result = asyncio.run(
        provider.chat(
            [Message(role="user", content="Hello")],
            audit_log=audit_log,
            session_id=session_id,
            user_id=1,
            turn_id=turn_id,
        )
    )

    assert result == "Done"
    assert audit_log.info.call_count == 3


def test_chat_raises_when_content_is_empty():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=None))]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    provider = _provider_with_mock_client(mock_client)

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
