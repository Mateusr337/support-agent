from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.repositories.audit_log_repository import AuditLogRepository


class AuditLogService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._repository = AuditLogRepository(db)

    def info(
        self,
        *,
        session_id: UUID,
        user_id: int,
        turn_id: UUID,
        type: str,
        message: str,
        data: dict | None = None,
    ) -> AuditLog:
        return self._create(
            session_id=session_id,
            user_id=user_id,
            turn_id=turn_id,
            type=type,
            status="info",
            message=message,
            data=data,
        )

    def warn(
        self,
        *,
        session_id: UUID,
        user_id: int,
        turn_id: UUID,
        type: str,
        message: str,
        data: dict | None = None,
    ) -> AuditLog:
        return self._create(
            session_id=session_id,
            user_id=user_id,
            turn_id=turn_id,
            type=type,
            status="warn",
            message=message,
            data=data,
        )

    def error(
        self,
        *,
        session_id: UUID,
        user_id: int,
        turn_id: UUID,
        type: str,
        message: str,
        data: dict | None = None,
    ) -> AuditLog:
        return self._create(
            session_id=session_id,
            user_id=user_id,
            turn_id=turn_id,
            type=type,
            status="error",
            message=message,
            data=data,
        )

    def list(
        self,
        *,
        session_id: UUID | None = None,
        user_id: int | None = None,
        turn_id: UUID | None = None,
    ) -> list[AuditLog]:
        return self._repository.list(
            session_id=session_id,
            user_id=user_id,
            turn_id=turn_id,
        )

    def _create(
        self,
        *,
        session_id: UUID,
        user_id: int,
        turn_id: UUID,
        type: str,
        status: str,
        message: str,
        data: dict | None = None,
    ) -> AuditLog:
        return self._repository.create(
            session_id=session_id,
            user_id=user_id,
            turn_id=turn_id,
            type=type,
            status=status,
            message=message,
            data=data,
        )
