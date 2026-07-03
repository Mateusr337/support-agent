from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

if TYPE_CHECKING:
    from app.services.audit_log_service import AuditLogService


@dataclass(frozen=True)
class Message:
    role: str
    content: str


class LLMProvider(Protocol):
    async def chat(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.2,
        audit_log: "AuditLogService | None" = None,
        session_id: UUID | None = None,
        user_id: int | None = None,
        turn_id: UUID | None = None,
    ) -> str: ...
