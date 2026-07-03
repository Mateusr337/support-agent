from uuid import uuid4

from app.models.chat_session import ChatSession
from app.repositories.user_repository import UserRepository
from app.core.security import hash_password
from app.services.audit_log_service import AuditLogService


def _create_user(db_session, email: str = "audit-service@example.com"):
    return UserRepository(db_session).create(
        email=email,
        name="Audit Service User",
        password_hash=hash_password("password123"),
    )


def test_info_warn_and_error_create_logs_with_status(db_session):
    user = _create_user(db_session)
    session = ChatSession(user_id=user.id)
    db_session.add(session)
    db_session.commit()

    service = AuditLogService(db_session)
    turn_id = uuid4()
    base_kwargs = {
        "session_id": session.id,
        "user_id": user.id,
        "turn_id": turn_id,
        "type": "tool_call",
        "message": "Tool invoked",
    }

    info_log = service.info(**base_kwargs, data={"tool": "search"})
    warn_log = service.warn(
        session_id=session.id,
        user_id=user.id,
        turn_id=turn_id,
        type="tool_call",
        message="Slow response",
    )
    error_log = service.error(
        session_id=session.id,
        user_id=user.id,
        turn_id=turn_id,
        type="tool_call",
        message="Tool failed",
    )

    assert info_log.status == "info"
    assert warn_log.status == "warn"
    assert error_log.status == "error"


def test_list_delegates_to_repository(db_session):
    user = _create_user(db_session, email="audit-list@example.com")
    session = ChatSession(user_id=user.id)
    db_session.add(session)
    db_session.commit()

    service = AuditLogService(db_session)
    turn_id = uuid4()
    service.info(
        session_id=session.id,
        user_id=user.id,
        turn_id=turn_id,
        type="agent_request",
        message="Processing",
    )
    db_session.commit()

    logs, has_more = service.list(session_id=session.id, user_id=user.id, turn_id=turn_id)
    assert len(logs) == 1
    assert logs[0].message == "Processing"
    assert has_more is False
