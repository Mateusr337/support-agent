from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.audit.schemas import AuditLogResponse
from app.api.v1.auth.dependencies import get_current_user
from app.api.v1.dependencies import get_audit_log_service
from app.api.v1.responses import UNAUTHORIZED_RESPONSE
from app.models.user import User
from app.services.audit_log_service import AuditLogService

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get(
    "/logs",
    status_code=status.HTTP_200_OK,
    response_model=list[AuditLogResponse],
    responses=UNAUTHORIZED_RESPONSE,
)
def list_audit_logs(
    current_user: User = Depends(get_current_user),
    service: AuditLogService = Depends(get_audit_log_service),
    session_id: UUID | None = Query(None, description="Filter by session ID"),
    turn_id: UUID | None = Query(None, description="Filter by turn ID"),
) -> list[AuditLogResponse]:
    logs = service.list(
        session_id=session_id,
        user_id=current_user.id,
        turn_id=turn_id,
    )
    return [AuditLogResponse.model_validate(log) for log in logs]
