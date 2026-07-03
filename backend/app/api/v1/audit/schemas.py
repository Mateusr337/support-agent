from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: UUID
    user_id: int
    turn_id: UUID
    type: str
    status: str
    message: str
    data: dict | None
    created_at: datetime
