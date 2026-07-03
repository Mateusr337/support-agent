from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chat_message import ChatMessage


class ChatMessageRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, message_id: int) -> ChatMessage | None:
        return self._db.get(ChatMessage, message_id)

    def list_by_session_id(self, session_id: UUID) -> list[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.chat_session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        return list(self._db.execute(stmt).scalars().all())

    def list_by_user_id(self, user_id: int) -> list[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.user_id == user_id)
            .order_by(ChatMessage.created_at.desc())
        )
        return list(self._db.execute(stmt).scalars().all())

    def create(
        self,
        chat_session_id: UUID,
        user_id: int,
        role: str,
        content: str,
    ) -> ChatMessage:
        message = ChatMessage(
            chat_session_id=chat_session_id,
            user_id=user_id,
            role=role,
            content=content,
        )
        self._db.add(message)
        self._db.flush()
        return message
