from fastapi import APIRouter

from app.api.v1.auth.routes import router as auth_router
from app.api.v1.chat.routes import router as chat_router
from app.api.v1.health.routes import router as health_router
from app.api.v1.users.routes import router as users_router
from app.api.v1.audit.routes import router as audit_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(chat_router)
router.include_router(health_router)
router.include_router(users_router)
router.include_router(audit_router)
