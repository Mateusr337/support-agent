from uuid import UUID

from app.agents.base import AgentConfig
from app.core.llm.base import LLMProvider, Message
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
        top_k: int = 5,
        temperature: float = 0.2,
        turn_id: UUID | None = None,
        session_id: UUID | None = None,
        user_id: int | None = None,
        audit_log: AuditLogService | None = None,
    ) -> str:
        if self._config.loop_mode == "tool_loop":
            raise NotImplementedError("Agent loop mode not implemented: tool_loop")

        context = await self._resolve_context(
            user_message,
            top_k=top_k,
            turn_id=turn_id,
            session_id=session_id,
            user_id=user_id,
            audit_log=audit_log,
        )
        messages = self._build_messages(user_message, history or [], context)
        return await self._llm.chat(
            messages,
            temperature=temperature,
            audit_log=audit_log,
            session_id=session_id,
            user_id=user_id,
            turn_id=turn_id,
        )

    async def _resolve_context(
        self,
        user_message: str,
        *,
        top_k: int,
        turn_id: UUID | None,
        session_id: UUID | None,
        user_id: int | None,
        audit_log: AuditLogService | None,
    ) -> str:
        tool_context = ToolContext(
            turn_id=turn_id,
            session_id=session_id,
            user_id=user_id,
            audit_log=audit_log,
        )
        parts: list[str] = []

        for binding in self._config.tools:
            if binding.invocation != "always":
                continue

            tool = self._tools[binding.name]
            result = await tool.run(
                self._build_always_arguments(binding.name, user_message, top_k=top_k),
                context=tool_context,
            )
            parts.append(result.content)

        if not parts:
            return "No relevant documents were found."

        return "\n\n".join(parts)

    def _build_always_arguments(
        self,
        tool_name: str,
        user_message: str,
        *,
        top_k: int,
    ) -> dict:
        if tool_name == "search_documents":
            return {"query": user_message, "top_k": top_k}
        raise NotImplementedError(f"Always invocation not defined for tool: {tool_name}")

    def _build_messages(
        self,
        user_message: str,
        history: list[Message],
        context: str,
    ) -> list[Message]:
        return [
            Message(role="system", content=self._config.prompt.format(context=context)),
            *history,
            Message(role="user", content=user_message),
        ]
