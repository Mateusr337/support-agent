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
        tool_context = ToolContext(
            turn_id=turn_id,
            session_id=session_id,
            user_id=user_id,
            audit_log=audit_log,
        )
        tool_definitions = [self._tools[name].definition for name in self._config.tools]
        messages = self._build_messages(user_message, history or [])

        for _ in range(self._config.max_tool_loop_iterations):
            completion = await self._llm.chat(
                messages,
                temperature=temperature,
                tools=tool_definitions or None,
                audit_log=audit_log,
                session_id=session_id,
                user_id=user_id,
                turn_id=turn_id,
            )

            if completion.tool_calls:
                messages.append(
                    Message(
                        role="assistant",
                        content=completion.content or "",
                        tool_calls=completion.tool_calls,
                    )
                )
                for tool_call in completion.tool_calls:
                    messages.append(
                        Message(
                            role="tool",
                            content=await self._run_tool_call(tool_call, tool_context),
                            tool_call_id=tool_call.id,
                        )
                    )
                continue

            if completion.content:
                return completion.content

            raise RuntimeError("LLM returned an empty response")

        raise RuntimeError("Maximum tool loop iterations exceeded")

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
