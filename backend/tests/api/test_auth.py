from app.core.security import create_access_token


def test_login_success(client, registered_user):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["user"]["email"] == registered_user["email"]
    assert data["user"]["name"] == registered_user["name"]


def test_login_wrong_password_returns_401(client, registered_user):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": registered_user["email"],
            "password": "wrongpassword",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_unknown_email_returns_401(client):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "missing@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_me_success(client, auth_headers, registered_user):
    response = client.get("/api/v1/auth/me", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == registered_user["email"]
    assert data["name"] == registered_user["name"]
    assert data["id"] == registered_user["id"]


def test_me_missing_token_returns_401(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_me_invalid_token_returns_401(client):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


def test_me_valid_token_unknown_user_returns_401(client):
    token = create_access_token(user_id=99999, email="ghost@example.com")
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "User not found"
