from uuid import uuid4

from app.models.audit_log import AuditLog
from app.models.chat_session import ChatSession
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.user_repository import UserRepository
from app.core.security import hash_password


def _create_user(db_session, email: str = "audit@example.com"):
    return UserRepository(db_session).create(
        email=email,
        name="Audit User",
        password_hash=hash_password("password123"),
    )


def test_create_and_list_with_filters(db_session):
    user = _create_user(db_session)
    session = ChatSession(user_id=user.id)
    db_session.add(session)
    db_session.commit()

    turn_a = uuid4()
    turn_b = uuid4()
    repository = AuditLogRepository(db_session)

    log_a = repository.create(
        session_id=session.id,
        user_id=user.id,
        turn_id=turn_a,
        type="agent_request",
        status="info",
        message="First turn",
    )
    repository.create(
        session_id=session.id,
        user_id=user.id,
        turn_id=turn_b,
        type="agent_response",
        status="info",
        message="Second turn",
    )
    db_session.commit()

    by_session = repository.list(session_id=session.id)
    assert len(by_session) == 2

    by_turn = repository.list(turn_id=turn_a)
    assert len(by_turn) == 1
    assert by_turn[0].id == log_a.id

    by_user = repository.list(user_id=user.id)
    assert len(by_user) == 2


def test_list_without_filters_returns_all_logs(db_session):
    user = _create_user(db_session, email="all-logs@example.com")
    session = ChatSession(user_id=user.id)
    db_session.add(session)
    db_session.commit()

    repository = AuditLogRepository(db_session)
    repository.create(
        session_id=session.id,
        user_id=user.id,
        turn_id=uuid4(),
        type="agent_request",
        status="info",
        message="Log entry",
    )
    db_session.commit()

    logs = repository.list()
    assert len(logs) == 1
    assert isinstance(logs[0], AuditLog)
