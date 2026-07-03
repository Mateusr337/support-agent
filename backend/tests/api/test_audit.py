from uuid import uuid4

from fastapi.testclient import TestClient

from app.models.audit_log import AuditLog
from app.models.chat_session import ChatSession


def test_list_audit_logs_success(client: TestClient, db_session, auth_headers, registered_user):
    session = ChatSession(user_id=registered_user["id"])
    db_session.add(session)
    db_session.commit()

    session_id = session.id
    turn_id = uuid4()

    log1 = AuditLog(
        session_id=session_id,
        user_id=registered_user["id"],
        turn_id=turn_id,
        type="agent_request",
        status="info",
        message="Test log 1",
        data={"key": "value1"},
    )
    log2 = AuditLog(
        session_id=session_id,
        user_id=registered_user["id"],
        turn_id=turn_id,
        type="agent_response",
        status="info",
        message="Test log 2",
        data={"key": "value2"},
    )
    db_session.add_all([log1, log2])
    db_session.commit()

    response = client.get("/api/v1/audit/logs", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2

    response = client.get(f"/api/v1/audit/logs?session_id={session_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["message"] == "Test log 2"
    assert data[1]["message"] == "Test log 1"


def test_list_audit_logs_without_auth_returns_401(client: TestClient):
    response = client.get("/api/v1/audit/logs")
    assert response.status_code == 401
