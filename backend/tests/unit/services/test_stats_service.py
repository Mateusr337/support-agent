from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest

from app.models.audit_log import AuditLog
from app.models.chat_session import ChatSession
from app.repositories.audit_log_repository import AuditLogRepository
from app.services.stats_service import InvalidStatsPeriodError, StatsService, _log_date, resolve_period


def _create_user(db_session, email: str = "stats@example.com"):
    from app.core.security import hash_password
    from app.repositories.user_repository import UserRepository

    return UserRepository(db_session).create(
        email=email,
        name="Stats User",
        password_hash=hash_password("password123"),
    )


def _seed_metrics_logs(db_session, user_id: int, session_id, turn_id):
    now = datetime.now(UTC)
    logs = [
        AuditLog(
            session_id=session_id,
            user_id=user_id,
            turn_id=turn_id,
            type="Token Usage",
            status="info",
            message="LLM token usage",
            data={
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
            created_at=now,
        ),
        AuditLog(
            session_id=session_id,
            user_id=user_id,
            turn_id=turn_id,
            type="Agent",
            status="info",
            message="LLM response",
            data={"latency_ms": 1200},
            created_at=now,
        ),
        AuditLog(
            session_id=session_id,
            user_id=user_id,
            turn_id=turn_id,
            type="Tool Result",
            status="info",
            message="Document search completed",
            data={"latency_ms": 300},
            created_at=now,
        ),
        AuditLog(
            session_id=session_id,
            user_id=user_id,
            turn_id=turn_id,
            type="Agent",
            status="info",
            message="Agent reply generated",
            data={"latency_ms": 2500, "reply_content": "Done"},
            created_at=now,
        ),
    ]
    db_session.add_all(logs)
    db_session.commit()


def test_list_for_metrics_filters_by_user_and_range(db_session):
    user = _create_user(db_session)
    other = _create_user(db_session, email="other@example.com")
    session = ChatSession(user_id=user.id)
    other_session = ChatSession(user_id=other.id)
    db_session.add_all([session, other_session])
    db_session.commit()

    turn_id = uuid4()
    now = datetime.now(UTC)
    in_range = AuditLog(
        session_id=session.id,
        user_id=user.id,
        turn_id=turn_id,
        type="Token Usage",
        status="info",
        message="LLM token usage",
        data={"total_tokens": 10, "prompt_tokens": 6, "completion_tokens": 4},
        created_at=now,
    )
    out_of_range = AuditLog(
        session_id=session.id,
        user_id=user.id,
        turn_id=turn_id,
        type="Token Usage",
        status="info",
        message="LLM token usage",
        data={"total_tokens": 99, "prompt_tokens": 50, "completion_tokens": 49},
        created_at=now - timedelta(days=10),
    )
    other_user = AuditLog(
        session_id=other_session.id,
        user_id=other.id,
        turn_id=uuid4(),
        type="Token Usage",
        status="info",
        message="LLM token usage",
        data={"total_tokens": 99, "prompt_tokens": 50, "completion_tokens": 49},
        created_at=now,
    )
    db_session.add_all([in_range, out_of_range, other_user])
    db_session.commit()

    repository = AuditLogRepository(db_session)
    rows = repository.list_for_metrics(
        user_id=user.id,
        from_dt=now - timedelta(days=1),
        to_dt=now + timedelta(minutes=1),
    )

    assert len(rows) == 1
    assert rows[0].data["total_tokens"] == 10


def test_list_for_metrics_filters_by_session_and_turn(db_session):
    user = _create_user(db_session)
    session_a = ChatSession(user_id=user.id)
    session_b = ChatSession(user_id=user.id)
    db_session.add_all([session_a, session_b])
    db_session.commit()

    turn_a = uuid4()
    turn_b = uuid4()
    now = datetime.now(UTC)

    db_session.add_all(
        [
            AuditLog(
                session_id=session_a.id,
                user_id=user.id,
                turn_id=turn_a,
                type="Agent",
                status="info",
                message="Test",
            ),
            AuditLog(
                session_id=session_b.id,
                user_id=user.id,
                turn_id=turn_b,
                type="Agent",
                status="info",
                message="Test",
            ),
        ]
    )
    db_session.commit()

    repository = AuditLogRepository(db_session)
    session_rows = repository.list_for_metrics(
        user_id=user.id,
        from_dt=now - timedelta(days=1),
        to_dt=now + timedelta(minutes=1),
        session_id=session_a.id,
    )
    turn_rows = repository.list_for_metrics(
        user_id=user.id,
        from_dt=now - timedelta(days=1),
        to_dt=now + timedelta(minutes=1),
        turn_id=turn_b,
    )

    assert len(session_rows) == 1
    assert session_rows[0].session_id == session_a.id
    assert len(turn_rows) == 1
    assert turn_rows[0].turn_id == turn_b


def test_get_metrics_aggregates_audit_logs(db_session):
    user = _create_user(db_session)
    session = ChatSession(user_id=user.id)
    db_session.add(session)
    db_session.commit()

    _seed_metrics_logs(db_session, user.id, session.id, uuid4())

    service = StatsService(db_session)
    metrics = service.get_metrics(user_id=user.id, period="today")

    assert metrics.total_tokens == 150
    assert metrics.turn_count == 1
    assert metrics.session_count == 1
    assert metrics.llm_call_count == 1
    assert metrics.tool_call_count == 1
    assert metrics.llm_call_latency_avg_ms == 1200
    assert metrics.tool_call_latency_avg_ms == 300
    assert metrics.turn_latency_avg_ms == 2500
    assert metrics.tokens_per_turn_avg == 150.0
    assert metrics.tokens_per_session_avg == 150.0
    assert metrics.tokens_per_turn_spread is not None
    assert metrics.tokens_per_turn_spread.min == 150


def test_get_metrics_returns_empty_summary_when_no_logs(db_session):
    user = _create_user(db_session)
    service = StatsService(db_session)
    metrics = service.get_metrics(user_id=user.id, period="today")

    assert metrics.total_tokens == 0
    assert metrics.turn_count == 0
    assert metrics.tokens_per_turn_spread is None
    assert metrics.turn_latency_avg_ms is None


def test_resolve_period_custom_range():
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 1, 2, tzinfo=UTC)
    period = resolve_period(period="today", from_dt=start, to_dt=end)

    assert period.preset is None
    assert period.from_dt == start
    assert period.to_dt == end


def test_resolve_period_rejects_invalid_range():
    start = datetime(2026, 1, 3, tzinfo=UTC)
    end = datetime(2026, 1, 1, tzinfo=UTC)
    with pytest.raises(InvalidStatsPeriodError):
        resolve_period(period="today", from_dt=start, to_dt=end)


def test_resolve_period_rejects_unknown_preset():
    with pytest.raises(InvalidStatsPeriodError):
        resolve_period(period="month", from_dt=None, to_dt=None)


def test_resolve_period_week_preset():
    period = resolve_period(period="week", from_dt=None, to_dt=None)
    assert period.preset == "week"


def test_get_metrics_ignores_logs_without_latency(db_session):
    user = _create_user(db_session)
    session = ChatSession(user_id=user.id)
    db_session.add(session)
    db_session.commit()

    db_session.add(
        AuditLog(
            session_id=session.id,
            user_id=user.id,
            turn_id=uuid4(),
            type="Agent",
            status="info",
            message="Processing user message",
            data={"content": "hello"},
        )
    )
    db_session.commit()

    service = StatsService(db_session)
    metrics = service.get_metrics(user_id=user.id, period="today")
    assert metrics.llm_call_count == 0


def test_resolve_period_accepts_naive_custom_range():
    start = datetime(2026, 1, 1)
    end = datetime(2026, 1, 2)
    period = resolve_period(period="today", from_dt=start, to_dt=end)
    assert period.from_dt.tzinfo == UTC


def test_log_date_converts_aware_datetime_to_utc_date():
    value = datetime(2026, 7, 7, 3, 0, tzinfo=UTC)

    assert _log_date(value) == date(2026, 7, 7)


def test_get_metrics_handles_naive_created_at(db_session):
    user = _create_user(db_session)
    session = ChatSession(user_id=user.id)
    db_session.add(session)
    db_session.commit()

    naive_now = datetime.now(UTC).replace(tzinfo=None)
    db_session.add(
        AuditLog(
            session_id=session.id,
            user_id=user.id,
            turn_id=uuid4(),
            type="Token Usage",
            status="info",
            message="LLM token usage",
            data={"total_tokens": 10, "prompt_tokens": 6, "completion_tokens": 4},
            created_at=naive_now,
        )
    )
    db_session.commit()

    service = StatsService(db_session)
    metrics = service.get_metrics(user_id=user.id, period="today")
    assert metrics.total_tokens == 10


def test_get_metrics_computes_spread_with_multiple_turns(db_session):
    user = _create_user(db_session)
    session = ChatSession(user_id=user.id)
    db_session.add(session)
    db_session.commit()

    now = datetime.now(UTC)
    for total in (100, 400):
        db_session.add(
            AuditLog(
                session_id=session.id,
                user_id=user.id,
                turn_id=uuid4(),
                type="Token Usage",
                status="info",
                message="LLM token usage",
                data={
                    "prompt_tokens": total // 2,
                    "completion_tokens": total // 2,
                    "total_tokens": total,
                },
                created_at=now,
            )
        )
    db_session.commit()

    service = StatsService(db_session)
    metrics = service.get_metrics(user_id=user.id, period="today")

    assert metrics.tokens_per_turn_spread is not None
    assert metrics.tokens_per_turn_spread.p50 == 250
    assert metrics.tokens_per_turn_spread.p95 >= metrics.tokens_per_turn_spread.p50
