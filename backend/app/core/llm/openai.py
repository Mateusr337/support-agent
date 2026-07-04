import json
import time
from collections.abc import AsyncIterator
from uuid import UUID

from openai import AsyncOpenAI

from app.core.llm.base import ChatCompletion, ChatStreamEvent, Message, ToolCallRequest
from app.services.audit_log_service import AuditLogService
from app.tools.base import ToolDefinition


class OpenAILLMProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def chat(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.2,
        tools: list[ToolDefinition] | None = None,
        audit_log: AuditLogService | None = None,
        session_id: UUID | None = None,
        user_id: int | None = None,
        turn_id: UUID | None = None,
    ) -> ChatCompletion:
        history = [self._to_openai_message(message) for message in messages]
        request_kwargs: dict = {
            "model": self._model,
            "messages": history,
            "temperature": temperature,
        }
        if tools:
            request_kwargs["tools"] = [self._to_openai_tool(tool) for tool in tools]

        self._audit_info(
            audit_log,
            session_id=session_id,
            user_id=user_id,
            turn_id=turn_id,
            type="Agent",
            message="LLM request",
            data={
                "model": self._model,
                "temperature": temperature,
                "message_count": len(messages),
                "messages": history,
                "tool_count": len(tools or []),
            },
        )

        start = time.perf_counter()
        response = await self._client.chat.completions.create(**request_kwargs)
        latency_ms = round((time.perf_counter() - start) * 1000)
        assistant_message = response.choices[0].message
        tool_calls = self._parse_tool_calls(assistant_message.tool_calls)
        completion = ChatCompletion(
            content=assistant_message.content,
            tool_calls=tool_calls,
        )

        if completion.content is None and not completion.tool_calls:
            raise RuntimeError("OpenAI returned an empty response")

        self._audit_info(
            audit_log,
            session_id=session_id,
            user_id=user_id,
            turn_id=turn_id,
            type="Agent",
            message="LLM response",
            data={
                "model": self._model,
                "content": completion.content,
                "latency_ms": latency_ms,
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "name": tool_call.name,
                        "arguments": tool_call.arguments,
                    }
                    for tool_call in completion.tool_calls
                ],
            },
        )

        if response.usage is not None:
            self._audit_info(
                audit_log,
                session_id=session_id,
                user_id=user_id,
                turn_id=turn_id,
                type="Token Usage",
                message="LLM token usage",
                data={
                    "model": self._model,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
            )

        return completion

    async def chat_stream(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.2,
        tools: list[ToolDefinition] | None = None,
        audit_log: AuditLogService | None = None,
        session_id: UUID | None = None,
        user_id: int | None = None,
        turn_id: UUID | None = None,
    ) -> AsyncIterator[ChatStreamEvent]:
        history = [self._to_openai_message(message) for message in messages]
        request_kwargs: dict = {
            "model": self._model,
            "messages": history,
            "temperature": temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tools:
            request_kwargs["tools"] = [self._to_openai_tool(tool) for tool in tools]

        self._audit_info(
            audit_log,
            session_id=session_id,
            user_id=user_id,
            turn_id=turn_id,
            type="Agent",
            message="LLM stream request",
            data={
                "model": self._model,
                "temperature": temperature,
                "message_count": len(messages),
                "messages": history,
                "tool_count": len(tools or []),
            },
        )

        stream = await self._client.chat.completions.create(**request_kwargs)
        stream_start = time.perf_counter()

        content_parts: list[str] = []
        tool_call_builders: dict[int, dict[str, str]] = {}
        usage = None
        async for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta
                if delta.content:
                    content_parts.append(delta.content)
                    yield ChatStreamEvent(content=delta.content)
                if delta.tool_calls:
                    for tool_call_delta in delta.tool_calls:
                        builder = tool_call_builders.setdefault(
                            tool_call_delta.index,
                            {"id": "", "name": "", "arguments": ""},
                        )
                        if tool_call_delta.id:
                            builder["id"] = tool_call_delta.id
                        if tool_call_delta.function:
                            if tool_call_delta.function.name:
                                builder["name"] = tool_call_delta.function.name
                            if tool_call_delta.function.arguments:
                                builder["arguments"] += tool_call_delta.function.arguments
            if chunk.usage is not None:
                usage = chunk.usage

        content = "".join(content_parts)
        tool_calls = self._parse_streamed_tool_calls(tool_call_builders)
        if not content and not tool_calls:
            raise RuntimeError("OpenAI returned an empty streamed response")

        if tool_calls:
            yield ChatStreamEvent(tool_calls=tool_calls)

        stream_latency_ms = round((time.perf_counter() - stream_start) * 1000)

        self._audit_info(
            audit_log,
            session_id=session_id,
            user_id=user_id,
            turn_id=turn_id,
            type="Agent",
            message="LLM stream response",
            data={
                "model": self._model,
                "content": content,
                "latency_ms": stream_latency_ms,
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "name": tool_call.name,
                        "arguments": tool_call.arguments,
                    }
                    for tool_call in tool_calls
                ],
            },
        )

        if usage is not None:
            self._audit_info(
                audit_log,
                session_id=session_id,
                user_id=user_id,
                turn_id=turn_id,
                type="Token Usage",
                message="LLM token usage",
                data={
                    "model": self._model,
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                },
            )

    def _to_openai_message(self, message: Message) -> dict:
        payload: dict = {"role": message.role, "content": message.content}
        if message.tool_calls:
            payload["tool_calls"] = [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.name,
                        "arguments": json.dumps(tool_call.arguments),
                    },
                }
                for tool_call in message.tool_calls
            ]
        if message.tool_call_id is not None:
            payload["tool_call_id"] = message.tool_call_id
        return payload

    def _to_openai_tool(self, tool: ToolDefinition) -> dict:
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }

    def _parse_tool_calls(self, tool_calls: list | None) -> tuple[ToolCallRequest, ...]:
        if not tool_calls:
            return ()

        parsed: list[ToolCallRequest] = []
        for tool_call in tool_calls:
            arguments = json.loads(tool_call.function.arguments or "{}")
            parsed.append(
                ToolCallRequest(
                    id=tool_call.id,
                    name=tool_call.function.name,
                    arguments=arguments,
                )
            )
        return tuple(parsed)

    def _parse_streamed_tool_calls(
        self,
        tool_call_builders: dict[int, dict[str, str]],
    ) -> tuple[ToolCallRequest, ...]:
        if not tool_call_builders:
            return ()

        parsed: list[ToolCallRequest] = []
        for index in sorted(tool_call_builders):
            builder = tool_call_builders[index]
            arguments = json.loads(builder["arguments"] or "{}")
            parsed.append(
                ToolCallRequest(
                    id=builder["id"],
                    name=builder["name"],
                    arguments=arguments,
                )
            )
        return tuple(parsed)

    def _audit_info(
        self,
        audit_log: AuditLogService | None,
        *,
        session_id: UUID | None,
        user_id: int | None,
        turn_id: UUID | None,
        type: str,
        message: str,
        data: dict,
    ) -> None:
        if (
            audit_log is None
            or session_id is None
            or user_id is None
            or turn_id is None
        ):
            return

        audit_log.info(
            session_id=session_id,
            user_id=user_id,
            turn_id=turn_id,
            type=type,
            message=message,
            data=data,
        )
