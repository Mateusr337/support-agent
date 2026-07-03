import bcrypt
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository


class UserAlreadyExistsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class UserService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._repository = UserRepository(db)

    def create_user(self, email: str, name: str, password: str) -> User:
        if self._repository.get_by_email(email):
            raise UserAlreadyExistsError(f"User with email {email} already exists")

        password_hash = hash_password(password)

        try:
            user = self._repository.create(
                email=email,
                name=name,
                password_hash=password_hash,
            )
            self._db.commit()
            self._db.refresh(user)
            return user
        except Exception:
            self._db.rollback()
            raise

    def authenticate_user(self, email: str, password: str) -> User:
        user = self._repository.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password")
        return user

    def get_user_by_id(self, user_id: int) -> User | None:
        return self._repository.get_by_id(user_id)
