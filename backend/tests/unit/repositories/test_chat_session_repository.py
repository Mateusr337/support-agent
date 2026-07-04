from datetime import UTC, datetime
from uuid import UUID

from app.core.security import hash_password
from app.models.chat_session import ChatSession
from app.repositories.chat_session_repository import ChatSessionRepository
from app.repositories.user_repository import UserRepository


def _create_user(db_session, email: str = "session-repo@example.com"):
    return UserRepository(db_session).create(
        email=email,
        name="Session Repo User",
        password_hash=hash_password("password123"),
    )


def test_get_by_id(db_session):
    user = _create_user(db_session)
    db_session.flush()

    repository = ChatSessionRepository(db_session)
    session = repository.create(user_id=user.id)
    db_session.commit()

    found = repository.get_by_id(session.id)
    assert found is not None
    assert found.id == session.id


def test_get_by_id_returns_none_when_missing(db_session):
    repository = ChatSessionRepository(db_session)

    assert repository.get_by_id(UUID("00000000-0000-0000-0000-000000000000")) is None


def test_get_by_id_and_user_id(db_session):
    user = _create_user(db_session)
    other = _create_user(db_session, email="other-session@example.com")
    db_session.flush()

    repository = ChatSessionRepository(db_session)
    session = repository.create(user_id=user.id)
    db_session.commit()

    found = repository.get_by_id_and_user_id(session.id, user.id)
    assert found is not None
    assert found.user_id == user.id

    assert repository.get_by_id_and_user_id(session.id, other.id) is None


def test_get_active_by_user_id_returns_latest_open_session(db_session):
    user = _create_user(db_session)
    db_session.flush()

    repository = ChatSessionRepository(db_session)
    older = repository.create(user_id=user.id)
    db_session.flush()
    older.updated_at = datetime(2024, 1, 1, tzinfo=UTC)

    newer = repository.create(user_id=user.id)
    db_session.commit()

    active = repository.get_active_by_user_id(user.id)
    assert active is not None
    assert active.id == newer.id


def test_get_active_by_user_id_skips_finalized_sessions(db_session):
    user = _create_user(db_session)
    db_session.flush()

    finalized = ChatSession(user_id=user.id, finalized_at=datetime.now(UTC))
    db_session.add(finalized)
    db_session.commit()

    repository = ChatSessionRepository(db_session)
    assert repository.get_active_by_user_id(user.id) is None


def test_list_by_user_id_orders_by_updated_at_desc(db_session):
    user = _create_user(db_session)
    db_session.flush()

    repository = ChatSessionRepository(db_session)
    first = repository.create(user_id=user.id)
    db_session.flush()
    first.updated_at = datetime(2024, 1, 1, tzinfo=UTC)

    second = repository.create(user_id=user.id)
    db_session.commit()

    sessions = repository.list_by_user_id(user.id)
    assert [session.id for session in sessions] == [second.id, first.id]


def test_create_and_update(db_session):
    user = _create_user(db_session)
    db_session.flush()

    repository = ChatSessionRepository(db_session)
    session = repository.create(user_id=user.id)
    session.finalized_at = datetime.now(UTC)
    updated = repository.update(session)
    db_session.commit()

    assert updated.finalized_at is not None
