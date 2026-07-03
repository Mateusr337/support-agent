from fastapi import APIRouter, Depends

from app.services.health_service import HealthService

router = APIRouter(prefix="/health", tags=["health"])


def get_health_service() -> HealthService:
    return HealthService()


@router.get("")
def health(service: HealthService = Depends(get_health_service)):
    return service.check()


@router.get("/db")
def health_db(service: HealthService = Depends(get_health_service)):
    return service.check_database()


@router.get("/qdrant")
def health_qdrant(service: HealthService = Depends(get_health_service)):
    return service.check_qdrant()
