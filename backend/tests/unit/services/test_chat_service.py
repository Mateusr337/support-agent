import asyncio
from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.llm.base import Message
from app.models.chat_session import ChatSession
from app.repositories.user_repository import UserRepository
from app.core.security import hash_password
from app.services.chat_service import (
    ChatService,
    ChatSessionFinalizedError,
    ChatSessionNotFoundError,
)


class FakeSupportAgent:
    def __init__(self, reply: str = "Agent reply") -> None:
        self._reply = reply
        self.last_user_message: str | None = None
        self.last_history: list[Message] | None = None

    async def reply(self, user_message: str, history=None, **kwargs) -> str:
        self.last_user_message = user_message
        self.last_history = history
        return self._reply


def _create_user(db_session, email: str = "chat@example.com"):
    return UserRepository(db_session).create(
        email=email,
        name="Chat User",
        password_hash=hash_password("password123"),
    )


def test_process_message_success(db_session):
    user = _create_user(db_session)
    db_session.flush()

    agent = FakeSupportAgent(reply="Agent reply")
    service = ChatService(db_session, agent)
    session = service.create_session(user_id=user.id)

    result = asyncio.run(
        service.process_message(
            session_id=session.id,
            user_id=user.id,
            content="I need help with my order",
        )
    )

    assert result.user_message.content == "I need help with my order"
    assert result.user_message.role == "user"
    assert result.assistant_message.content == "Agent reply"
    assert result.assistant_message.role == "assistant"
    assert result.user_message.chat_session_id == session.id
    assert result.assistant_message.chat_session_id == session.id
    assert agent.last_user_message == "I need help with my order"
    assert agent.last_history == []


def test_process_message_passes_prior_history(db_session):
    user = _create_user(db_session)
    db_session.flush()

    agent = FakeSupportAgent()
    service = ChatService(db_session, agent)
    session = service.create_session(user_id=user.id)

    asyncio.run(
        service.process_message(
            session_id=session.id,
            user_id=user.id,
            content="First question",
        )
    )
    asyncio.run(
        service.process_message(
            session_id=session.id,
            user_id=user.id,
            content="Follow-up question",
        )
    )

    assert agent.last_user_message == "Follow-up question"
    assert agent.last_history == [
        Message(role="user", content="First question"),
        Message(role="assistant", content="Agent reply"),
    ]


def test_process_message_session_not_found_raises(db_session):
    user = _create_user(db_session)
    db_session.flush()

    service = ChatService(db_session, FakeSupportAgent())

    with pytest.raises(ChatSessionNotFoundError):
        asyncio.run(
            service.process_message(
                session_id=uuid4(),
                user_id=user.id,
                content="Hello",
            )
        )


def test_process_message_wrong_user_raises(db_session):
    owner = _create_user(db_session, email="owner@example.com")
    other = _create_user(db_session, email="other@example.com")
    db_session.flush()

    service = ChatService(db_session, FakeSupportAgent())
    session = service.create_session(user_id=owner.id)

    with pytest.raises(ChatSessionNotFoundError):
        asyncio.run(
            service.process_message(
                session_id=session.id,
                user_id=other.id,
                content="Hello",
            )
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

    service = ChatService(db_session, FakeSupportAgent())

    with pytest.raises(ChatSessionFinalizedError):
        asyncio.run(
            service.process_message(
                session_id=session.id,
                user_id=user.id,
                content="Hello",
            )
        )


def test_list_session_messages_returns_latest_page(db_session):
    user = _create_user(db_session)
    db_session.flush()

    service = ChatService(db_session, FakeSupportAgent())
    session = service.create_session(user_id=user.id)

    for index in range(3):
        asyncio.run(
            service.process_message(
                session_id=session.id,
                user_id=user.id,
                content=f"Message {index + 1}",
            )
        )

    messages, has_more = service.list_session_messages(
        session_id=session.id,
        user_id=user.id,
        limit=4,
    )

    assert has_more is True
    assert len(messages) == 4
    assert messages[0].content == "Message 2"
    assert messages[-1].role == "assistant"


def test_list_session_messages_paginates_with_offset(db_session):
    user = _create_user(db_session)
    db_session.flush()

    service = ChatService(db_session, FakeSupportAgent())
    session = service.create_session(user_id=user.id)

    for index in range(3):
        asyncio.run(
            service.process_message(
                session_id=session.id,
                user_id=user.id,
                content=f"Message {index + 1}",
            )
        )

    first_page, has_more = service.list_session_messages(
        session_id=session.id,
        user_id=user.id,
        limit=4,
    )
    assert has_more is True

    second_page, has_more_again = service.list_session_messages(
        session_id=session.id,
        user_id=user.id,
        limit=4,
        offset=first_page[0].id,
    )

    assert has_more_again is False
    assert len(second_page) == 2
    assert second_page[0].content == "Message 1"


def test_list_session_messages_session_not_found_raises(db_session):
    user = _create_user(db_session)
    db_session.flush()

    service = ChatService(db_session, FakeSupportAgent())

    with pytest.raises(ChatSessionNotFoundError):
        service.list_session_messages(
            session_id=uuid4(),
            user_id=user.id,
        )


def test_create_session_success(db_session):
    user = _create_user(db_session)
    db_session.flush()

    service = ChatService(db_session, FakeSupportAgent())
    session = service.create_session(user_id=user.id)

    assert session.id is not None
    assert session.user_id == user.id
    assert session.finalized_at is None


def test_get_or_create_active_session_returns_existing(db_session):
    user = _create_user(db_session)
    db_session.flush()

    service = ChatService(db_session, FakeSupportAgent())
    created = service.create_session(user_id=user.id)
    found = service.get_or_create_active_session(user_id=user.id)

    assert found.id == created.id


def test_create_session_rolls_back_on_commit_error(db_session, monkeypatch):
    user = _create_user(db_session)
    db_session.flush()

    service = ChatService(db_session, FakeSupportAgent())
    monkeypatch.setattr(
        service._db,
        "commit",
        MagicMock(side_effect=RuntimeError("commit failed")),
    )

    with pytest.raises(RuntimeError, match="commit failed"):
        service.create_session(user_id=user.id)


def test_get_or_create_active_session_rolls_back_on_commit_error(db_session, monkeypatch):
    user = _create_user(db_session)
    db_session.flush()

    service = ChatService(db_session, FakeSupportAgent())
    monkeypatch.setattr(
        service._session_repository,
        "get_active_by_user_id",
        MagicMock(return_value=None),
    )
    monkeypatch.setattr(
        service._db,
        "commit",
        MagicMock(side_effect=RuntimeError("commit failed")),
    )

    with pytest.raises(RuntimeError, match="commit failed"):
        service.get_or_create_active_session(user_id=user.id)


def test_process_message_rolls_back_on_agent_error(db_session):
    class FailingAgent:
        async def reply(self, *args, **kwargs) -> str:
            raise RuntimeError("agent failed")

    user = _create_user(db_session)
    db_session.flush()

    service = ChatService(db_session, FailingAgent())
    session = service.create_session(user_id=user.id)

    with pytest.raises(RuntimeError, match="agent failed"):
        asyncio.run(
            service.process_message(
                session_id=session.id,
                user_id=user.id,
                content="Hello",
            )
        )


def test_finalize_session_marks_active_session_finalized(db_session):
    user = _create_user(db_session)
    db_session.flush()

    service = ChatService(db_session, FakeSupportAgent())
    session = service.create_session(user_id=user.id)

    finalized = service.finalize_session(user_id=user.id)

    assert finalized is not None
    assert finalized.id == session.id
    assert finalized.finalized_at is not None


def test_finalize_session_not_found_raises(db_session):
    user = _create_user(db_session)
    db_session.flush()

    service = ChatService(db_session, FakeSupportAgent())

    with pytest.raises(ChatSessionNotFoundError):
        service.finalize_session(user_id=user.id)


def test_finalize_session_already_finalized_raises(db_session, monkeypatch):
    user = _create_user(db_session)
    db_session.flush()

    service = ChatService(db_session, FakeSupportAgent())
    session = service.create_session(user_id=user.id)
    session.finalized_at = datetime.now(UTC)
    monkeypatch.setattr(
        service._session_repository,
        "get_active_by_user_id",
        MagicMock(return_value=session),
    )

    with pytest.raises(ChatSessionFinalizedError):
        service.finalize_session(user_id=user.id)


def test_reload_session_finalizes_active_and_creates_new(db_session):
    user = _create_user(db_session)
    db_session.flush()

    service = ChatService(db_session, FakeSupportAgent())
    old_session = service.create_session(user_id=user.id)

    new_session = service.reload_session(user_id=user.id)

    assert new_session.id != old_session.id
    db_session.refresh(old_session)
    assert old_session.finalized_at is not None
    assert new_session.finalized_at is None


def test_reload_session_not_found_raises(db_session):
    user = _create_user(db_session)
    db_session.flush()

    service = ChatService(db_session, FakeSupportAgent())

    with pytest.raises(ChatSessionNotFoundError):
        service.reload_session(user_id=user.id)


def test_reload_session_rolls_back_on_commit_error(db_session, monkeypatch):
    user = _create_user(db_session)
    db_session.flush()

    service = ChatService(db_session, FakeSupportAgent())
    service.create_session(user_id=user.id)
    monkeypatch.setattr(
        service._db,
        "commit",
        MagicMock(side_effect=RuntimeError("commit failed")),
    )

    with pytest.raises(RuntimeError, match="commit failed"):
        service.reload_session(user_id=user.id)
