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
        type="Agent",
        status="info",
        message="First turn",
    )
    repository.create(
        session_id=session.id,
        user_id=user.id,
        turn_id=turn_b,
        type="Tool Result",
        status="info",
        message="Second turn",
    )
    db_session.commit()

    by_session, _ = repository.list(session_id=session.id)
    assert len(by_session) == 2

    by_turn, _ = repository.list(turn_id=turn_a)
    assert len(by_turn) == 1
    assert by_turn[0].id == log_a.id

    by_user, _ = repository.list(user_id=user.id)
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
        type="Agent",
        status="info",
        message="Log entry",
    )
    db_session.commit()

    logs, has_more = repository.list()
    assert len(logs) == 1
    assert isinstance(logs[0], AuditLog)
    assert has_more is False


def test_list_paginates_with_offset(db_session):
    user = _create_user(db_session, email="paginated@example.com")
    session = ChatSession(user_id=user.id)
    db_session.add(session)
    db_session.commit()

    repository = AuditLogRepository(db_session)
    for index in range(5):
        repository.create(
            session_id=session.id,
            user_id=user.id,
            turn_id=uuid4(),
            type="Agent",
            status="info",
            message=f"Log {index}",
        )
    db_session.commit()

    first_page, has_more = repository.list(user_id=user.id, limit=3)
    assert len(first_page) == 3
    assert has_more is True
    assert first_page[0].message == "Log 4"

    second_page, has_more_again = repository.list(
        user_id=user.id,
        limit=3,
        offset=first_page[-1].id,
    )
    assert len(second_page) == 2
    assert has_more_again is False
    assert second_page[-1].message == "Log 0"


def test_list_for_metrics_filters_by_date_range(db_session):
    from datetime import UTC, datetime, timedelta

    user = _create_user(db_session)
    session = ChatSession(user_id=user.id)
    db_session.add(session)
    db_session.commit()

    turn_id = uuid4()
    now = datetime.now(UTC)
    repository = AuditLogRepository(db_session)
    repository.create(
        session_id=session.id,
        user_id=user.id,
        turn_id=turn_id,
        type="Token Usage",
        status="info",
        message="LLM token usage",
        data={"total_tokens": 5, "prompt_tokens": 3, "completion_tokens": 2},
    )
    db_session.commit()

    rows = repository.list_for_metrics(
        user_id=user.id,
        from_dt=now - timedelta(hours=1),
        to_dt=now + timedelta(hours=1),
    )
    assert len(rows) == 1
