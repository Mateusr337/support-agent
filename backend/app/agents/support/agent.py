from collections.abc import AsyncIterator
from uuid import UUID

from app.agents.base import AgentConfig
from app.core.llm.base import LLMProvider, Message, ToolCallRequest
from app.services.audit_log_service import AuditLogService
from app.tools.base import Tool, ToolContext


class SupportAgent:
    def __init__(self, llm: LLMProvider, config: AgentConfig, tools: dict[str, Tool]) -> None:
        self._llm = llm
        self._config = config
        self._tools = tools

    async def reply(
        self,
        user_message: str,
        history: list[Message] | None = None,
        *,
        temperature: float = 0.2,
        turn_id: UUID | None = None,
        session_id: UUID | None = None,
        user_id: int | None = None,
        audit_log: AuditLogService | None = None,
    ) -> str:
        parts: list[str] = []
        async for event in self.reply_stream(
            user_message,
            history=history,
            temperature=temperature,
            turn_id=turn_id,
            session_id=session_id,
            user_id=user_id,
            audit_log=audit_log,
        ):
            if event["type"] == "token":
                parts.append(event["content"])
        return "".join(parts)

    async def reply_stream(
        self,
        user_message: str,
        history: list[Message] | None = None,
        *,
        temperature: float = 0.2,
        turn_id: UUID | None = None,
        session_id: UUID | None = None,
        user_id: int | None = None,
        audit_log: AuditLogService | None = None,
    ) -> AsyncIterator[dict]:
        tool_context = ToolContext(
            turn_id=turn_id,
            session_id=session_id,
            user_id=user_id,
            audit_log=audit_log,
        )
        tool_definitions = [self._tools[name].definition for name in self._config.tools]
        messages = self._build_messages(user_message, history or [])
        max_iterations = self._config.max_tool_loop_iterations
        llm_kwargs = {
            "temperature": temperature,
            "audit_log": audit_log,
            "session_id": session_id,
            "user_id": user_id,
            "turn_id": turn_id,
        }

        for iteration in range(max_iterations):
            is_last_iteration = iteration == max_iterations - 1
            stream_tools = None if is_last_iteration else (tool_definitions or None)
            tool_calls: tuple[ToolCallRequest, ...] = ()

            async for event in self._llm.chat_stream(
                messages,
                tools=stream_tools,
                **llm_kwargs,
            ):
                if event.content:
                    yield {"type": "token", "content": event.content}
                if event.tool_calls:
                    tool_calls = event.tool_calls

            if not tool_calls:
                return

            messages.append(
                Message(
                    role="assistant",
                    content="",
                    tool_calls=tool_calls,
                )
            )
            for tool_call in tool_calls:
                yield {"type": "tool_call", "name": tool_call.name}
                messages.append(
                    Message(
                        role="tool",
                        content=await self._run_tool_call(tool_call, tool_context),
                        tool_call_id=tool_call.id,
                    )
                )

    async def _run_tool_call(
        self,
        tool_call: ToolCallRequest,
        tool_context: ToolContext,
    ) -> str:
        tool = self._tools.get(tool_call.name)
        if tool is None:
            return f"Unknown tool: {tool_call.name}"

        result = await tool.run(tool_call.arguments, context=tool_context)
        return result.content

    def _build_messages(self, user_message: str, history: list[Message]) -> list[Message]:
        return [
            Message(role="system", content=self._config.prompt),
            *history,
            Message(role="user", content=user_message),
        ]
