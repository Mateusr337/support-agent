from uuid import uuid4

from fastapi.testclient import TestClient

from app.models.audit_log import AuditLog
from app.models.chat_session import ChatSession


def _seed_stats_logs(db_session, user_id: int):
    session = ChatSession(user_id=user_id)
    db_session.add(session)
    db_session.commit()

    turn_id = uuid4()
    db_session.add(
        AuditLog(
            session_id=session.id,
            user_id=user_id,
            turn_id=turn_id,
            type="Token Usage",
            status="info",
            message="LLM token usage",
            data={
                "prompt_tokens": 200,
                "completion_tokens": 100,
                "total_tokens": 300,
            },
        )
    )
    db_session.add(
        AuditLog(
            session_id=session.id,
            user_id=user_id,
            turn_id=turn_id,
            type="Agent",
            status="info",
            message="Agent reply generated",
            data={"latency_ms": 1800, "reply_content": "Hello"},
        )
    )
    db_session.commit()


def test_get_stats_metrics_success(client: TestClient, db_session, auth_headers, registered_user):
    _seed_stats_logs(db_session, registered_user["id"])

    response = client.get("/api/v1/stats/metrics?period=today", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["summary"]["total_tokens"] == 300
    assert data["summary"]["turn_count"] == 1
    assert data["latency_ms"]["turn_avg_ms"] == 1800
    assert len(data["tokens_by_day"]) >= 1
    assert len(data["distributions"]["tokens_per_turn"]) == 4


def test_get_stats_metrics_week_period(client: TestClient, auth_headers, registered_user):
    response = client.get("/api/v1/stats/metrics?period=week", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["period"]["preset"] == "week"


def test_get_stats_metrics_without_auth_returns_401(client: TestClient):
    response = client.get("/api/v1/stats/metrics")
    assert response.status_code == 401


def test_get_stats_metrics_is_scoped_to_current_user(
    client: TestClient,
    db_session,
    auth_headers,
    registered_user,
):
    other_payload = {
        "email": "other-stats@example.com",
        "name": "Other",
        "password": "password123",
    }
    other_response = client.post("/api/v1/users", json=other_payload)
    assert other_response.status_code == 201
    _seed_stats_logs(db_session, other_response.json()["id"])

    response = client.get("/api/v1/stats/metrics?period=today", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["summary"]["total_tokens"] == 0
