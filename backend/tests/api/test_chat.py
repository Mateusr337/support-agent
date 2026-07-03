def test_create_conversation_success(client, auth_headers, registered_user):
    response = client.post("/api/v1/chat/conversations", headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == registered_user["id"]
    assert data["finalized_at"] is None
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_conversation_without_auth_returns_401(client):
    response = client.post("/api/v1/chat/conversations")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_get_or_create_active_conversation_creates_when_missing(client, auth_headers, registered_user):
    response = client.get("/api/v1/chat/conversations/active", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == registered_user["id"]
    assert data["finalized_at"] is None


def test_get_or_create_active_conversation_returns_existing(client, auth_headers, registered_user):
    create_response = client.post("/api/v1/chat/conversations", headers=auth_headers)
    assert create_response.status_code == 201
    session_id = create_response.json()["id"]

    response = client.get("/api/v1/chat/conversations/active", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == session_id
    assert data["finalized_at"] is None


def test_get_or_create_active_conversation_skips_finalized_session(
    client,
    auth_headers,
    db_session,
):
    from datetime import UTC, datetime

    from app.models.chat_session import ChatSession
    from app.repositories.user_repository import UserRepository
    from app.core.security import hash_password

    user = UserRepository(db_session).create(
        email="finalized@example.com",
        name="Finalized User",
        password_hash=hash_password("password123"),
    )
    db_session.flush()

    finalized_session = ChatSession(
        user_id=user.id,
        finalized_at=datetime.now(UTC),
    )
    db_session.add(finalized_session)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "finalized@example.com", "password": "password123"},
    )
    assert login_response.status_code == 200
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    response = client.get("/api/v1/chat/conversations/active", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] != str(finalized_session.id)


def test_get_or_create_active_conversation_without_auth_returns_401(client):
    response = client.get("/api/v1/chat/conversations/active")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_create_conversation_invalid_token_returns_401(client):
    response = client.post(
        "/api/v1/chat/conversations",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


def test_get_or_create_active_conversation_invalid_token_returns_401(client):
    response = client.get(
        "/api/v1/chat/conversations/active",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


def test_send_message_success(client, auth_headers, registered_user):
    create_response = client.post("/api/v1/chat/conversations", headers=auth_headers)
    assert create_response.status_code == 201
    session_id = create_response.json()["id"]

    response = client.post(
        f"/api/v1/chat/conversations/{session_id}/messages",
        headers=auth_headers,
        json={"content": "Hello, I need help"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["user_message"]["content"] == "Hello, I need help"
    assert data["user_message"]["role"] == "user"
    assert data["user_message"]["user_id"] == registered_user["id"]
    assert data["user_message"]["chat_session_id"] == session_id
    assert data["assistant_message"]["role"] == "assistant"
    assert data["assistant_message"]["content"] == (
        "Thanks for your message. A support agent will help you shortly."
    )
    assert data["assistant_message"]["chat_session_id"] == session_id


def test_send_message_session_not_found_returns_404(client, auth_headers):
    response = client.post(
        "/api/v1/chat/conversations/00000000-0000-0000-0000-000000000000/messages",
        headers=auth_headers,
        json={"content": "Hello"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Chat session not found"


def test_send_message_finalized_session_returns_400(client, auth_headers, db_session):
    from datetime import UTC, datetime

    from app.models.chat_session import ChatSession
    from app.repositories.user_repository import UserRepository
    from app.core.security import hash_password

    user = UserRepository(db_session).create(
        email="finalized-msg@example.com",
        name="Finalized Msg User",
        password_hash=hash_password("password123"),
    )
    db_session.flush()

    finalized_session = ChatSession(
        user_id=user.id,
        finalized_at=datetime.now(UTC),
    )
    db_session.add(finalized_session)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "finalized-msg@example.com", "password": "password123"},
    )
    assert login_response.status_code == 200
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    response = client.post(
        f"/api/v1/chat/conversations/{finalized_session.id}/messages",
        headers=headers,
        json={"content": "Hello"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Chat session is finalized"


def test_send_message_empty_content_returns_422(client, auth_headers):
    create_response = client.post("/api/v1/chat/conversations", headers=auth_headers)
    assert create_response.status_code == 201
    session_id = create_response.json()["id"]

    response = client.post(
        f"/api/v1/chat/conversations/{session_id}/messages",
        headers=auth_headers,
        json={"content": ""},
    )

    assert response.status_code == 422


def test_send_message_without_auth_returns_401(client):
    response = client.post(
        "/api/v1/chat/conversations/00000000-0000-0000-0000-000000000000/messages",
        json={"content": "Hello"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"
