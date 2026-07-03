from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.dependencies import get_health_service
from app.api.v1.responses import SERVICE_UNAVAILABLE_RESPONSE
from app.services.health_service import HealthService

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "",
    status_code=status.HTTP_200_OK,
)
def health(service: HealthService = Depends(get_health_service)):
    return service.check()


@router.get(
    "/db",
    status_code=status.HTTP_200_OK,
    responses=SERVICE_UNAVAILABLE_RESPONSE,
)
def health_db(service: HealthService = Depends(get_health_service)):
    try:
        return service.check_database()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from exc


@router.get(
    "/qdrant",
    status_code=status.HTTP_200_OK,
    responses=SERVICE_UNAVAILABLE_RESPONSE,
)
def health_qdrant(service: HealthService = Depends(get_health_service)):
    try:
        return service.check_qdrant()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Qdrant unavailable",
        ) from exc
