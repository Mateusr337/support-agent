import asyncio
import json
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

    async def reply_stream(self, user_message: str, history=None, **kwargs):
        self.last_user_message = user_message
        self.last_history = history
        yield {"type": "token", "content": self._reply}

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


async def _collect_stream(service: ChatService, **kwargs) -> list[dict]:
    events: list[dict] = []
    async for event in service.process_message_stream(**kwargs):
        events.append(event)
    return events


def _run_stream(service: ChatService, **kwargs) -> list[dict]:
    return asyncio.run(_collect_stream(service, **kwargs))


def test_ensure_session_active_success(db_session):
    user = _create_user(db_session)
    db_session.flush()

    service = ChatService(db_session, FakeSupportAgent())
    session = service.create_session(user_id=user.id)

    active = service.ensure_session_active(session.id, user.id)

    assert active.id == session.id


def test_ensure_session_active_not_found_raises(db_session):
    user = _create_user(db_session)
    db_session.flush()

    service = ChatService(db_session, FakeSupportAgent())

    with pytest.raises(ChatSessionNotFoundError):
        service.ensure_session_active(uuid4(), user.id)


def test_ensure_session_active_finalized_raises(db_session):
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
        service.ensure_session_active(session.id, user.id)


def test_process_message_stream_success(db_session):
    user = _create_user(db_session)
    db_session.flush()

    agent = FakeSupportAgent(reply="Agent reply")
    service = ChatService(db_session, agent)
    session = service.create_session(user_id=user.id)

    events = _run_stream(
        service,
        session_id=session.id,
        user_id=user.id,
        content="I need help with my order",
    )

    assert events[0]["type"] == "turn_started"
    assert events[1]["type"] == "token"
    assert events[-1]["type"] == "done"
    assert events[-1]["content"] == "Agent reply"
    assert agent.last_user_message == "I need help with my order"
    assert agent.last_history == []


def test_process_message_stream_passes_prior_history(db_session):
    user = _create_user(db_session)
    db_session.flush()

    agent = FakeSupportAgent()
    service = ChatService(db_session, agent)
    session = service.create_session(user_id=user.id)

    _run_stream(
        service,
        session_id=session.id,
        user_id=user.id,
        content="First question",
    )
    _run_stream(
        service,
        session_id=session.id,
        user_id=user.id,
        content="Follow-up question",
    )

    assert agent.last_user_message == "Follow-up question"
    assert agent.last_history == [
        Message(role="user", content="First question"),
        Message(role="assistant", content="Agent reply"),
    ]


def test_process_message_stream_session_not_found_raises(db_session):
    user = _create_user(db_session)
    db_session.flush()

    service = ChatService(db_session, FakeSupportAgent())

    with pytest.raises(ChatSessionNotFoundError):
        _run_stream(
            service,
            session_id=uuid4(),
            user_id=user.id,
            content="Hello",
        )


def test_process_message_stream_wrong_user_raises(db_session):
    owner = _create_user(db_session, email="owner@example.com")
    other = _create_user(db_session, email="other@example.com")
    db_session.flush()

    service = ChatService(db_session, FakeSupportAgent())
    session = service.create_session(user_id=owner.id)

    with pytest.raises(ChatSessionNotFoundError):
        _run_stream(
            service,
            session_id=session.id,
            user_id=other.id,
            content="Hello",
        )


def test_process_message_stream_finalized_session_raises(db_session):
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
        _run_stream(
            service,
            session_id=session.id,
            user_id=user.id,
            content="Hello",
        )


def test_list_session_messages_returns_latest_page(db_session):
    user = _create_user(db_session)
    db_session.flush()

    service = ChatService(db_session, FakeSupportAgent())
    session = service.create_session(user_id=user.id)

    for index in range(3):
        _run_stream(
            service,
            session_id=session.id,
            user_id=user.id,
            content=f"Message {index + 1}",
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
        _run_stream(
            service,
            session_id=session.id,
            user_id=user.id,
            content=f"Message {index + 1}",
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


def test_process_message_stream_rolls_back_on_agent_error(db_session):
    class FailingAgent:
        async def reply_stream(self, *args, **kwargs):
            yield {"type": "token", "content": "partial"}
            raise RuntimeError("agent failed")

    user = _create_user(db_session)
    db_session.flush()

    service = ChatService(db_session, FailingAgent())
    session = service.create_session(user_id=user.id)

    with pytest.raises(RuntimeError, match="agent failed"):
        _run_stream(
            service,
            session_id=session.id,
            user_id=user.id,
            content="Hello",
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
