from sqlalchemy.orm import Session

from app.models.chat_session import ChatSession
from app.repositories.chat_session_repository import ChatSessionRepository


class ChatService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._session_repository = ChatSessionRepository(db)

    def create_session(self, user_id: int) -> ChatSession:
        try:
            session = self._session_repository.create(user_id=user_id)
            self._db.commit()
            self._db.refresh(session)
            return session
        except Exception:
            self._db.rollback()
            raise

    def get_or_create_active_session(self, user_id: int) -> ChatSession:
        try:
            session = self._session_repository.get_active_by_user_id(user_id)
            if session is not None:
                return session

            session = self._session_repository.create(user_id=user_id)
            self._db.commit()
            self._db.refresh(session)
            return session
        except Exception:
            self._db.rollback()
            raise
