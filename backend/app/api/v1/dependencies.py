from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.chat_service import ChatService
from app.services.health_service import HealthService
from app.services.user_service import UserService


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)


def get_chat_service(db: Session = Depends(get_db)) -> ChatService:
    return ChatService(db)


def get_health_service() -> HealthService:
    return HealthService()
