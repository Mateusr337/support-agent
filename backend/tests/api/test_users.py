def test_register_user_success(client):
    response = client.post(
        "/api/v1/users",
        json={
            "email": "new@example.com",
            "name": "New User",
            "password": "securepass",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@example.com"
    assert data["name"] == "New User"
    assert "id" in data
    assert "created_at" in data
    assert "password" not in data
    assert "password_hash" not in data


def test_register_duplicate_email_returns_409(client, registered_user):
    response = client.post(
        "/api/v1/users",
        json={
            "email": registered_user["email"],
            "name": "Another User",
            "password": "anotherpass",
        },
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_register_invalid_email_returns_422(client):
    response = client.post(
        "/api/v1/users",
        json={
            "email": "not-an-email",
            "name": "User",
            "password": "password123",
        },
    )

    assert response.status_code == 422


def test_register_short_password_returns_422(client):
    response = client.post(
        "/api/v1/users",
        json={
            "email": "short@example.com",
            "name": "User",
            "password": "short",
        },
    )

    assert response.status_code == 422


def test_register_empty_name_returns_422(client):
    response = client.post(
        "/api/v1/users",
        json={
            "email": "empty-name@example.com",
            "name": "",
            "password": "password123",
        },
    )

    assert response.status_code == 422


def test_register_missing_fields_returns_422(client):
    response = client.post("/api/v1/users", json={"email": "missing@example.com"})

    assert response.status_code == 422
