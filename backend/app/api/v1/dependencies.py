from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.agents.support_agent import SupportAgent
from app.core.database import get_db
from app.core.llm.factory import get_llm_provider
from app.rag.retriever import NoOpRetriever
from app.services.audit_log_service import AuditLogService
from app.services.chat_service import ChatService
from app.services.health_service import HealthService
from app.services.user_service import UserService


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)


def get_audit_log_service(db: Session = Depends(get_db)) -> AuditLogService:
    return AuditLogService(db)


@lru_cache
def get_support_agent() -> SupportAgent:
    return SupportAgent(
        llm=get_llm_provider(),
        retriever=NoOpRetriever(),
    )


def get_chat_service(
    db: Session = Depends(get_db),
    agent: SupportAgent = Depends(get_support_agent),
) -> ChatService:
    return ChatService(db, agent)


def get_health_service() -> HealthService:
    return HealthService()
