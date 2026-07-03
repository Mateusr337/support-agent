from fastapi import APIRouter, Depends, status

from app.api.v1.auth.dependencies import get_current_user
from app.api.v1.chat.schemas import ChatSessionResponse
from app.api.v1.dependencies import get_chat_service
from app.api.v1.responses import UNAUTHORIZED_RESPONSE
from app.models.user import User
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat/conversations", tags=["chat"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ChatSessionResponse,
    responses=UNAUTHORIZED_RESPONSE,
)
def create_conversation(
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> ChatSessionResponse:
    session = service.create_session(user_id=current_user.id)
    return ChatSessionResponse.model_validate(session)


@router.get(
    "/active",
    status_code=status.HTTP_200_OK,
    response_model=ChatSessionResponse,
    responses=UNAUTHORIZED_RESPONSE,
)
def get_or_create_active_conversation(
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> ChatSessionResponse:
    session = service.get_or_create_active_session(user_id=current_user.id)
    return ChatSessionResponse.model_validate(session)
