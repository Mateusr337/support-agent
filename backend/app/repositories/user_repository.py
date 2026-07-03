from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self._db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return self._db.execute(stmt).scalar_one_or_none()

    def create(self, email: str, name: str, password_hash: str) -> User:
        user = User(
            email=email,
            name=name,
            password_hash=password_hash,
        )
        self._db.add(user)
        self._db.flush()
        return user
