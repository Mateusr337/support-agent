from app.core.security import hash_password
from app.repositories.chat_message_repository import ChatMessageRepository
from app.repositories.chat_session_repository import ChatSessionRepository
from app.repositories.user_repository import UserRepository


def _create_user_and_session(db_session, email: str = "message-repo@example.com"):
    user = UserRepository(db_session).create(
        email=email,
        name="Message Repo User",
        password_hash=hash_password("password123"),
    )
    db_session.flush()
    session = ChatSessionRepository(db_session).create(user_id=user.id)
    db_session.commit()
    return user, session


def test_get_by_id(db_session):
    user, session = _create_user_and_session(db_session)

    repository = ChatMessageRepository(db_session)
    message = repository.create(
        chat_session_id=session.id,
        user_id=user.id,
        role="user",
        content="Hello",
    )
    db_session.commit()

    found = repository.get_by_id(message.id)
    assert found is not None
    assert found.content == "Hello"


def test_get_by_id_returns_none_when_missing(db_session):
    repository = ChatMessageRepository(db_session)

    assert repository.get_by_id(9999) is None


def test_list_by_session_id_without_limit_returns_all_messages(db_session):
    user, session = _create_user_and_session(db_session)
    repository = ChatMessageRepository(db_session)

    first = repository.create(
        chat_session_id=session.id,
        user_id=user.id,
        role="user",
        content="First",
    )
    second = repository.create(
        chat_session_id=session.id,
        user_id=user.id,
        role="assistant",
        content="Second",
    )
    db_session.commit()

    messages, has_more = repository.list_by_session_id(session.id)
    assert has_more is False
    assert [message.id for message in messages] == [first.id, second.id]


def test_list_by_session_id_paginates_with_limit_and_offset(db_session):
    user, session = _create_user_and_session(db_session)
    repository = ChatMessageRepository(db_session)

    message_ids = []
    for index in range(3):
        message = repository.create(
            chat_session_id=session.id,
            user_id=user.id,
            role="user",
            content=f"Message {index + 1}",
        )
        message_ids.append(message.id)
    db_session.commit()

    first_page, has_more = repository.list_by_session_id(
        session.id,
        limit=2,
    )
    assert has_more is True
    assert len(first_page) == 2

    second_page, has_more_again = repository.list_by_session_id(
        session.id,
        limit=2,
        offset=first_page[0].id,
    )
    assert has_more_again is False
    assert len(second_page) == 1
    assert second_page[0].id == message_ids[0]


def test_list_by_user_id(db_session):
    user, session = _create_user_and_session(db_session)
    other_user = UserRepository(db_session).create(
        email="other-message@example.com",
        name="Other",
        password_hash=hash_password("password123"),
    )
    db_session.flush()
    other_session = ChatSessionRepository(db_session).create(user_id=other_user.id)
    db_session.commit()

    repository = ChatMessageRepository(db_session)
    user_message = repository.create(
        chat_session_id=session.id,
        user_id=user.id,
        role="user",
        content="User message",
    )
    repository.create(
        chat_session_id=other_session.id,
        user_id=other_user.id,
        role="user",
        content="Other message",
    )
    db_session.commit()

    messages = repository.list_by_user_id(user.id)
    assert len(messages) == 1
    assert messages[0].id == user_message.id
