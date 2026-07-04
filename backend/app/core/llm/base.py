from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol
from uuid import UUID

if TYPE_CHECKING:
    from app.services.audit_log_service import AuditLogService
    from app.tools.base import ToolDefinition


@dataclass(frozen=True)
class ToolCallRequest:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ChatCompletion:
    content: str | None
    tool_calls: tuple[ToolCallRequest, ...] = ()


@dataclass(frozen=True)
class Message:
    role: str
    content: str
    tool_calls: tuple[ToolCallRequest, ...] = ()
    tool_call_id: str | None = None


class LLMProvider(Protocol):
    async def chat(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.2,
        tools: "list[ToolDefinition] | None" = None,
        audit_log: "AuditLogService | None" = None,
        session_id: UUID | None = None,
        user_id: int | None = None,
        turn_id: UUID | None = None,
    ) -> ChatCompletion: ...
