from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.agents.support_agent import SupportAgent
from app.core.llm.base import Message
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.repositories.chat_message_repository import ChatMessageRepository
from app.repositories.chat_session_repository import ChatSessionRepository
from app.services.audit_log_service import AuditLogService


class ChatSessionNotFoundError(Exception):
    pass


class ChatSessionFinalizedError(Exception):
    pass


@dataclass(frozen=True)
class ProcessMessageResult:
    user_message: ChatMessage
    assistant_message: ChatMessage


class ChatService:
    def __init__(self, db: Session, agent: SupportAgent) -> None:
        self._db = db
        self._agent = agent
        self._session_repository = ChatSessionRepository(db)
        self._message_repository = ChatMessageRepository(db)
        self._audit_log = AuditLogService(db)

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

    def list_session_messages(
        self,
        session_id: UUID,
        user_id: int,
        limit: int = 10,
        offset: int | None = None,
    ) -> tuple[list[ChatMessage], bool]:
        session = self._session_repository.get_by_id_and_user_id(session_id, user_id)
        if session is None:
            raise ChatSessionNotFoundError("Chat session not found")

        return self._message_repository.list_by_session_id(
            session_id=session_id,
            limit=limit,
            offset=offset,
        )

    async def process_message(
        self,
        session_id: UUID,
        user_id: int,
        content: str,
    ) -> ProcessMessageResult:
        session = self._session_repository.get_by_id_and_user_id(session_id, user_id)
        if session is None:
            raise ChatSessionNotFoundError("Chat session not found")

        if session.finalized_at is not None:
            raise ChatSessionFinalizedError("Chat session is finalized")

        try:
            session.updated_at = datetime.now(UTC)

            prior_messages, _ = self._message_repository.list_by_session_id(session_id)
            history = self._to_llm_history(prior_messages)
            turn_id = uuid4()

            user_message = self._message_repository.create(
                chat_session_id=session_id,
                user_id=user_id,
                role="user",
                content=content,
            )
            self._audit_log.info(
                session_id=session_id,
                user_id=user_id,
                turn_id=turn_id,
                type="agent_request",
                message="Processing user message",
            )
            reply = await self._agent.reply(
                content,
                history=history,
                turn_id=turn_id,
                session_id=session_id,
                user_id=user_id,
                audit_log=self._audit_log,
            )
            self._audit_log.info(
                session_id=session_id,
                user_id=user_id,
                turn_id=turn_id,
                type="agent_response",
                message="Agent reply generated",
            )
            assistant_message = self._message_repository.create(
                chat_session_id=session_id,
                user_id=user_id,
                role="assistant",
                content=reply,
            )
            self._db.commit()
            self._db.refresh(user_message)
            self._db.refresh(assistant_message)
            return ProcessMessageResult(
                user_message=user_message,
                assistant_message=assistant_message,
            )
        except Exception:
            self._db.rollback()
            raise

    def _to_llm_history(self, messages: list[ChatMessage]) -> list[Message]:
        return [
            Message(role=message.role, content=message.content)
            for message in messages
            if message.role in ("user", "assistant")
        ]
