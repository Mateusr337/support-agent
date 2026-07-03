from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditLogRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
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
        log = AuditLog(
            session_id=session_id,
            user_id=user_id,
            turn_id=turn_id,
            type=type,
            status=status,
            message=message,
            data=data,
        )
        self._db.add(log)
        self._db.flush()
        return log

    def list(
        self,
        *,
        session_id: UUID | None = None,
        user_id: int | None = None,
        turn_id: UUID | None = None,
    ) -> list[AuditLog]:
        stmt = select(AuditLog)
        if session_id is not None:
            stmt = stmt.where(AuditLog.session_id == session_id)
        if user_id is not None:
            stmt = stmt.where(AuditLog.user_id == user_id)
        if turn_id is not None:
            stmt = stmt.where(AuditLog.turn_id == turn_id)
        stmt = stmt.order_by(AuditLog.created_at.desc())
        return list(self._db.execute(stmt).scalars().all())
