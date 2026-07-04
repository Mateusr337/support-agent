from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chat_session import ChatSession


class ChatSessionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, session_id: UUID) -> ChatSession | None:
        return self._db.get(ChatSession, session_id)

    def get_by_id_and_user_id(self, session_id: UUID, user_id: int) -> ChatSession | None:
        stmt = select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def get_active_by_user_id(self, user_id: int) -> ChatSession | None:
        stmt = (
            select(ChatSession)
            .where(
                ChatSession.user_id == user_id,
                ChatSession.finalized_at.is_(None),
            )
            .order_by(ChatSession.updated_at.desc())
            .limit(1)
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def list_by_user_id(self, user_id: int) -> list[ChatSession]:
        stmt = (
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
        )
        return list(self._db.execute(stmt).scalars().all())

    def create(self, user_id: int) -> ChatSession:
        session = ChatSession(user_id=user_id)
        self._db.add(session)
        self._db.flush()
        return session

    def update(self, session: ChatSession) -> ChatSession:
        self._db.flush()
        return session
