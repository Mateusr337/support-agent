from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from app.services.audit_log_service import AuditLogService


@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    source: str | None = None


@dataclass(frozen=True)
class ToolContext:
    turn_id: UUID | None = None
    session_id: UUID | None = None
    user_id: int | None = None
    audit_log: AuditLogService | None = None


@dataclass(frozen=True)
class ToolResult:
    content: str
    data: dict[str, Any] | None = None


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]


class Tool(Protocol):
    @property
    def definition(self) -> ToolDefinition: ...

    async def run(self, arguments: dict[str, Any], *, context: ToolContext) -> ToolResult: ...
