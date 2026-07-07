from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def _metrics_bound(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


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
        return log

    def list(
        self,
        *,
        session_id: UUID | None = None,
        user_id: int | None = None,
        turn_id: UUID | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> tuple[list[AuditLog], bool]:
        stmt = select(AuditLog)
        if session_id is not None:
            stmt = stmt.where(AuditLog.session_id == session_id)
        if user_id is not None:
            stmt = stmt.where(AuditLog.user_id == user_id)
        if turn_id is not None:
            stmt = stmt.where(AuditLog.turn_id == turn_id)

        if limit is None:
            stmt = stmt.order_by(AuditLog.created_at.desc())
            return list(self._db.execute(stmt).scalars().all()), False

        if offset is not None:
            stmt = stmt.where(AuditLog.id < offset)
        stmt = stmt.order_by(AuditLog.id.desc()).limit(limit + 1)
        rows = list(self._db.execute(stmt).scalars().all())
        has_more = len(rows) > limit
        return rows[:limit], has_more

    def list_for_metrics(
        self,
        *,
        user_id: int,
        from_dt: datetime,
        to_dt: datetime,
        session_id: UUID | None = None,
        turn_id: UUID | None = None,
    ) -> list[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(
                AuditLog.user_id == user_id,
                AuditLog.created_at >= _metrics_bound(from_dt),
                AuditLog.created_at <= _metrics_bound(to_dt),
            )
            .order_by(AuditLog.created_at.asc())
        )
        if session_id is not None:
            stmt = stmt.where(AuditLog.session_id == session_id)
        if turn_id is not None:
            stmt = stmt.where(AuditLog.turn_id == turn_id)
        return list(self._db.execute(stmt).scalars().all())
