from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.models.chat_session import ChatSession
from app.repositories.user_repository import UserRepository
from app.core.security import hash_password
from app.services.chat_service import (
    STUB_REPLY,
    ChatService,
    ChatSessionFinalizedError,
    ChatSessionNotFoundError,
)


def _create_user(db_session, email: str = "chat@example.com"):
    return UserRepository(db_session).create(
        email=email,
        name="Chat User",
        password_hash=hash_password("password123"),
    )


def test_process_message_success(db_session):
    user = _create_user(db_session)
    db_session.flush()

    service = ChatService(db_session)
    session = service.create_session(user_id=user.id)

    result = service.process_message(
        session_id=session.id,
        user_id=user.id,
        content="I need help with my order",
    )

    assert result.user_message.content == "I need help with my order"
    assert result.user_message.role == "user"
    assert result.assistant_message.content == STUB_REPLY
    assert result.assistant_message.role == "assistant"
    assert result.user_message.chat_session_id == session.id
    assert result.assistant_message.chat_session_id == session.id


def test_process_message_session_not_found_raises(db_session):
    user = _create_user(db_session)
    db_session.flush()

    service = ChatService(db_session)

    with pytest.raises(ChatSessionNotFoundError):
        service.process_message(
            session_id=uuid4(),
            user_id=user.id,
            content="Hello",
        )


def test_process_message_wrong_user_raises(db_session):
    owner = _create_user(db_session, email="owner@example.com")
    other = _create_user(db_session, email="other@example.com")
    db_session.flush()

    service = ChatService(db_session)
    session = service.create_session(user_id=owner.id)

    with pytest.raises(ChatSessionNotFoundError):
        service.process_message(
            session_id=session.id,
            user_id=other.id,
            content="Hello",
        )


def test_process_message_finalized_session_raises(db_session):
    user = _create_user(db_session)
    db_session.flush()

    session = ChatSession(
        user_id=user.id,
        finalized_at=datetime.now(UTC),
    )
    db_session.add(session)
    db_session.commit()

    service = ChatService(db_session)

    with pytest.raises(ChatSessionFinalizedError):
        service.process_message(
            session_id=session.id,
            user_id=user.id,
            content="Hello",
        )
