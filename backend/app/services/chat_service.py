from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.agents.support import SupportAgent
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


LLM_HISTORY_MESSAGE_LIMIT = 15


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

    def ensure_session_active(self, session_id: UUID, user_id: int) -> ChatSession:
        session = self._session_repository.get_by_id_and_user_id(session_id, user_id)
        if session is None:
            raise ChatSessionNotFoundError("Chat session not found")
        if session.finalized_at is not None:
            raise ChatSessionFinalizedError("Chat session is finalized")
        return session

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

    async def process_message_stream(
        self,
        session_id: UUID,
        user_id: int,
        content: str,
    ) -> AsyncIterator[dict]:
        session = self.ensure_session_active(session_id, user_id)
        turn_id = uuid4()

        yield {"type": "turn_started", "turn_id": str(turn_id)}

        try:
            session.updated_at = datetime.now(UTC)

            prior_messages, _ = self._message_repository.list_by_session_id(
                session_id,
                limit=LLM_HISTORY_MESSAGE_LIMIT,
            )
            history = self._to_llm_history(prior_messages)

            self._message_repository.create(
                chat_session_id=session_id,
                user_id=user_id,
                role="user",
                content=content,
            )
            self._audit_log.info(
                session_id=session_id,
                user_id=user_id,
                turn_id=turn_id,
                type="Agent",
                message="Processing user message",
                data={"content": content},
            )

            reply_parts: list[str] = []
            async for event in self._agent.reply_stream(
                content,
                history=history,
                turn_id=turn_id,
                session_id=session_id,
                user_id=user_id,
                audit_log=self._audit_log,
            ):
                if event["type"] == "token":
                    reply_parts.append(event["content"])
                yield event

            reply = "".join(reply_parts)
            self._audit_log.info(
                session_id=session_id,
                user_id=user_id,
                turn_id=turn_id,
                type="Agent",
                message="Agent reply generated",
                data={"reply_content": reply},
            )
            assistant_message = self._message_repository.create(
                chat_session_id=session_id,
                user_id=user_id,
                role="assistant",
                content=reply,
            )
            self._db.commit()
            self._db.refresh(assistant_message)

            yield {
                "type": "done",
                "assistant_message_id": assistant_message.id,
                "content": reply,
            }
        except Exception:
            self._db.rollback()
            raise

    def finalize_session(self, user_id: int) -> ChatSession | None:
        session = self._session_repository.get_active_by_user_id(user_id)
        if session is None:
            raise ChatSessionNotFoundError("Chat session not found")
        if session.finalized_at is not None:
            raise ChatSessionFinalizedError("Chat session is already finalized")
        session.finalized_at = datetime.now(UTC)
        self._session_repository.update(session)
        return session

    def reload_session(self, user_id: int) -> ChatSession:
        try:
            self.finalize_session(user_id)
            new_session = self._session_repository.create(user_id=user_id)
            self._db.commit()
            self._db.refresh(new_session)
            return new_session
        except Exception:
            self._db.rollback()
            raise

    def _to_llm_history(self, messages: list[ChatMessage]) -> list[Message]:
        return [
            Message(role=message.role, content=message.content)
            for message in messages
            if message.role in ("user", "assistant")
        ]
