from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_password():
    password = "my-secret-password"
    password_hash = hash_password(password)

    assert password_hash != password
    assert verify_password(password, password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_create_and_decode_access_token():
    token = create_access_token(user_id=42, email="user@example.com")
    payload = decode_access_token(token)

    assert payload["sub"] == "42"
    assert payload["email"] == "user@example.com"
    assert "exp" in payload


def test_decode_expired_token_raises():
    expired = datetime.now(UTC) - timedelta(minutes=1)
    payload = {
        "sub": "1",
        "email": "user@example.com",
        "exp": expired,
    }
    token = jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)
