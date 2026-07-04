import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.llm.base import ChatCompletion, ChatStreamEvent, Message, ToolCallRequest
from app.core.llm.factory import get_llm_provider
from app.core.llm.openai import OpenAILLMProvider
from app.tools.base import ToolDefinition


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
        type="Agent",
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
        type="Token Usage",
        message="LLM token usage",
        data={"total_tokens": 15},
    )

    audit_log.info.assert_called_once_with(
        session_id=session_id,
        user_id=1,
        turn_id=turn_id,
        type="Token Usage",
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

    assert result == ChatCompletion(content="Reset the printer.")
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

    assert result == ChatCompletion(content="Done")
    assert audit_log.info.call_count == 3
    response_log = audit_log.info.call_args_list[1].kwargs
    assert response_log["message"] == "LLM response"
    assert isinstance(response_log["data"]["latency_ms"], int)


def test_chat_stream_yields_token_deltas():
    async def fake_stream():
        chunk_one = MagicMock()
        chunk_one.choices = [
            MagicMock(delta=MagicMock(content="Hello", tool_calls=None))
        ]
        chunk_one.usage = None
        chunk_two = MagicMock()
        chunk_two.choices = [
            MagicMock(delta=MagicMock(content=" world", tool_calls=None))
        ]
        chunk_two.usage = None
        yield chunk_one
        yield chunk_two

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=fake_stream())

    provider = _provider_with_mock_client(mock_client)
    tokens, _ = asyncio.run(_collect_stream(provider))

    assert tokens == ["Hello", " world"]
    mock_client.chat.completions.create.assert_awaited_once_with(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hi"}],
        temperature=0.2,
        stream=True,
        stream_options={"include_usage": True},
    )


def test_chat_stream_passes_tools_when_provided():
    async def fake_stream():
        chunk = MagicMock()
        chunk.choices = [MagicMock(delta=MagicMock(content="Done", tool_calls=None))]
        chunk.usage = None
        yield chunk

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=fake_stream())

    tool = ToolDefinition(
        name="search_documents",
        description="Search manuals",
        parameters={"type": "object", "properties": {}},
    )

    provider = _provider_with_mock_client(mock_client)
    tokens, _ = asyncio.run(_collect_stream(provider, tools=[tool]))

    assert tokens == ["Done"]
    mock_client.chat.completions.create.assert_awaited_once_with(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hi"}],
        temperature=0.2,
        stream=True,
        stream_options={"include_usage": True},
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "search_documents",
                    "description": "Search manuals",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ],
    )


def test_chat_stream_yields_tool_calls_from_stream_deltas():
    function_one = MagicMock()
    function_one.name = "search_documents"
    function_one.arguments = '{"query":'

    function_two = MagicMock()
    function_two.name = None
    function_two.arguments = ' "reset"}'

    async def fake_stream():
        chunk_one = MagicMock()
        chunk_one.choices = [
            MagicMock(
                delta=MagicMock(
                    content=None,
                    tool_calls=[
                        MagicMock(
                            index=0,
                            id="call_1",
                            function=function_one,
                        )
                    ],
                )
            )
        ]
        chunk_one.usage = None
        chunk_two = MagicMock()
        chunk_two.choices = [
            MagicMock(
                delta=MagicMock(
                    content=None,
                    tool_calls=[
                        MagicMock(
                            index=0,
                            id=None,
                            function=function_two,
                        )
                    ],
                )
            )
        ]
        chunk_two.usage = None
        yield chunk_one
        yield chunk_two

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=fake_stream())
    provider = _provider_with_mock_client(mock_client)

    tokens, tool_calls = asyncio.run(_collect_stream(provider))

    assert tokens == []
    assert len(tool_calls) == 1
    assert tool_calls[0].id == "call_1"
    assert tool_calls[0].name == "search_documents"
    assert tool_calls[0].arguments == {"query": "reset"}


def test_chat_stream_logs_token_usage_when_context_is_provided():
    async def fake_stream():
        chunk_one = MagicMock()
        chunk_one.choices = [
            MagicMock(delta=MagicMock(content="Hello", tool_calls=None))
        ]
        chunk_one.usage = None
        chunk_two = MagicMock()
        chunk_two.choices = []
        chunk_two.usage = MagicMock(
            prompt_tokens=20,
            completion_tokens=8,
            total_tokens=28,
        )
        yield chunk_one
        yield chunk_two

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=fake_stream())

    audit_log = MagicMock()
    session_id = uuid4()
    turn_id = uuid4()
    provider = _provider_with_mock_client(mock_client)

    tokens, _ = asyncio.run(
        _collect_stream(
            provider,
            audit_log=audit_log,
            session_id=session_id,
            user_id=1,
            turn_id=turn_id,
        )
    )

    assert tokens == ["Hello"]
    assert audit_log.info.call_count == 3
    stream_response = next(
        call.kwargs
        for call in audit_log.info.call_args_list
        if call.kwargs.get("message") == "LLM stream response"
    )
    assert isinstance(stream_response["data"]["latency_ms"], int)
    audit_log.info.assert_any_call(
        session_id=session_id,
        user_id=1,
        turn_id=turn_id,
        type="Token Usage",
        message="LLM token usage",
        data={
            "model": "gpt-4o-mini",
            "prompt_tokens": 20,
            "completion_tokens": 8,
            "total_tokens": 28,
        },
    )


async def _collect_stream(
    provider: OpenAILLMProvider,
    *,
    audit_log=None,
    session_id=None,
    user_id=None,
    turn_id=None,
    tools=None,
) -> tuple[list[str], tuple[ToolCallRequest, ...]]:
    tokens: list[str] = []
    tool_calls: tuple[ToolCallRequest, ...] = ()
    async for event in provider.chat_stream(
        [Message(role="user", content="Hi")],
        temperature=0.2,
        tools=tools,
        audit_log=audit_log,
        session_id=session_id,
        user_id=user_id,
        turn_id=turn_id,
    ):
        if event.content:
            tokens.append(event.content)
        if event.tool_calls:
            tool_calls = event.tool_calls
    return tokens, tool_calls


def test_chat_stream_raises_when_empty():
    async def fake_stream():
        chunk = MagicMock()
        chunk.choices = [
            MagicMock(delta=MagicMock(content=None, tool_calls=None))
        ]
        chunk.usage = None
        yield chunk

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=fake_stream())
    provider = _provider_with_mock_client(mock_client)

    with pytest.raises(RuntimeError, match="empty streamed response"):
        asyncio.run(_collect_stream(provider))


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
