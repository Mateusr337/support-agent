from unittest.mock import MagicMock

import pytest

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.services.user_service import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserService,
)


def test_create_user_success(db_session):
    service = UserService(db_session)

    user = service.create_user(
        email="service@example.com",
        name="Service User",
        password="password123",
    )

    assert user.id is not None
    assert user.email == "service@example.com"
    assert verify_password("password123", user.password_hash)


def test_create_user_duplicate_email_raises(db_session):
    service = UserService(db_session)
    service.create_user(
        email="dup@example.com",
        name="First",
        password="password123",
    )

    with pytest.raises(UserAlreadyExistsError):
        service.create_user(
            email="dup@example.com",
            name="Second",
            password="password456",
        )


def test_create_user_rolls_back_on_repository_error(db_session, monkeypatch):
    service = UserService(db_session)
    monkeypatch.setattr(
        service._repository,
        "create",
        MagicMock(side_effect=RuntimeError("db failure")),
    )

    with pytest.raises(RuntimeError, match="db failure"):
        service.create_user(
            email="fail@example.com",
            name="Fail",
            password="password123",
        )


def test_authenticate_user_success(db_session):
    service = UserService(db_session)
    service.create_user(
        email="auth@example.com",
        name="Auth User",
        password="password123",
    )

    user = service.authenticate_user("auth@example.com", "password123")

    assert user.email == "auth@example.com"


def test_authenticate_user_wrong_password_raises(db_session):
    service = UserService(db_session)
    service.create_user(
        email="wrong@example.com",
        name="Wrong Pass",
        password="password123",
    )

    with pytest.raises(InvalidCredentialsError):
        service.authenticate_user("wrong@example.com", "bad-password")


def test_authenticate_user_unknown_email_raises(db_session):
    service = UserService(db_session)

    with pytest.raises(InvalidCredentialsError):
        service.authenticate_user("missing@example.com", "password123")


def test_get_user_by_id(db_session):
    service = UserService(db_session)
    created = service.create_user(
        email="lookup@example.com",
        name="Lookup",
        password="password123",
    )

    found = service.get_user_by_id(created.id)

    assert found is not None
    assert found.email == "lookup@example.com"


def test_get_user_by_id_returns_none(db_session):
    service = UserService(db_session)

    assert service.get_user_by_id(9999) is None


def test_create_user_with_mocked_repository(db_session, monkeypatch):
    mock_repo = MagicMock()
    mock_repo.get_by_email.return_value = None
    mock_repo.create.return_value = User(
        id=1,
        email="mock@example.com",
        name="Mock",
        password_hash=hash_password("password123"),
    )
    monkeypatch.setattr(db_session, "commit", lambda: None)
    monkeypatch.setattr(db_session, "refresh", lambda *args, **kwargs: None)

    service = UserService(db_session)
    service._repository = mock_repo

    user = service.create_user(
        email="mock@example.com",
        name="Mock",
        password="password123",
    )

    assert user.email == "mock@example.com"
    mock_repo.get_by_email.assert_called_once_with("mock@example.com")
    mock_repo.create.assert_called_once()
