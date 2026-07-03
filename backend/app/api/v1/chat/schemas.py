from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: int
    created_at: datetime
    updated_at: datetime
    finalized_at: datetime | None


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=8000)


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chat_session_id: UUID
    user_id: int
    role: str
    content: str
    created_at: datetime


class SendMessageResponse(BaseModel):
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse


class ChatMessagesPageResponse(BaseModel):
    items: list[ChatMessageResponse]
    has_more: bool
