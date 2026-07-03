from app.core.security import hash_password
from app.repositories.user_repository import UserRepository


def test_create_and_get_by_email(db_session):
    repository = UserRepository(db_session)
    password_hash = hash_password("password123")

    user = repository.create(
        email="repo@example.com",
        name="Repo User",
        password_hash=password_hash,
    )
    db_session.commit()

    assert user.id is not None
    assert user.email == "repo@example.com"

    found = repository.get_by_email("repo@example.com")
    assert found is not None
    assert found.id == user.id
    assert found.name == "Repo User"


def test_get_by_email_returns_none_when_missing(db_session):
    repository = UserRepository(db_session)

    assert repository.get_by_email("missing@example.com") is None


def test_get_by_id(db_session):
    repository = UserRepository(db_session)
    user = repository.create(
        email="byid@example.com",
        name="By ID",
        password_hash=hash_password("password123"),
    )
    db_session.commit()

    found = repository.get_by_id(user.id)
    assert found is not None
    assert found.email == "byid@example.com"


def test_get_by_id_returns_none_when_missing(db_session):
    repository = UserRepository(db_session)

    assert repository.get_by_id(9999) is None
