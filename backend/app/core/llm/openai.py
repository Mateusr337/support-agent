import json
from uuid import UUID

from openai import AsyncOpenAI

from app.core.llm.base import ChatCompletion, Message, ToolCallRequest
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

        response = await self._client.chat.completions.create(**request_kwargs)
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
