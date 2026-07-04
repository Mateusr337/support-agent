from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.api.v1.auth.dependencies import get_current_user
from app.api.v1.chat.schemas import (
    ChatMessagesPageResponse,
    ChatMessageResponse,
    ChatSessionResponse,
    SendMessageRequest,
)
from app.api.v1.dependencies import get_chat_service
from app.api.v1.responses import (
    BAD_REQUEST_RESPONSE,
    NOT_FOUND_RESPONSE,
    UNAUTHORIZED_RESPONSE,
    VALIDATION_ERROR_RESPONSE,
    merge_responses,
)
from app.core.streaming.sse import SSE_HEADERS, format_sse
from app.models.user import User
from app.services.chat_service import (
    ChatService,
    ChatSessionFinalizedError,
    ChatSessionNotFoundError,
)

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


@router.post(
    "/reload",
    status_code=status.HTTP_201_CREATED,
    response_model=ChatSessionResponse,
    responses=merge_responses(
        UNAUTHORIZED_RESPONSE,
        NOT_FOUND_RESPONSE,
        BAD_REQUEST_RESPONSE,
        VALIDATION_ERROR_RESPONSE,
    ),
)
def reload_conversation(
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> ChatSessionResponse:
    try:
        session = service.reload_session(user_id=current_user.id)
    except ChatSessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ChatSessionFinalizedError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
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


@router.get(
    "/{session_id}/messages",
    status_code=status.HTTP_200_OK,
    response_model=ChatMessagesPageResponse,
    responses=merge_responses(UNAUTHORIZED_RESPONSE, NOT_FOUND_RESPONSE),
)
def list_messages(
    session_id: UUID,
    limit: int = Query(default=10, ge=1, le=50),
    offset: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> ChatMessagesPageResponse:
    try:
        messages, has_more = service.list_session_messages(
            session_id=session_id,
            user_id=current_user.id,
            limit=limit,
            offset=offset,
        )
    except ChatSessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return ChatMessagesPageResponse(
        items=[ChatMessageResponse.model_validate(message) for message in messages],
        has_more=has_more,
    )


@router.post(
    "/{session_id}/messages",
    status_code=status.HTTP_200_OK,
    responses=merge_responses(
        UNAUTHORIZED_RESPONSE,
        NOT_FOUND_RESPONSE,
        BAD_REQUEST_RESPONSE,
        VALIDATION_ERROR_RESPONSE,
    ),
)
async def send_message(
    session_id: UUID,
    body: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    try:
        service.ensure_session_active(session_id, current_user.id)
    except ChatSessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ChatSessionFinalizedError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    async def event_generator():
        try:
            async for event in service.process_message_stream(
                session_id=session_id,
                user_id=current_user.id,
                content=body.content,
            ):
                yield format_sse(event)
        except Exception as exc:
            yield format_sse({"type": "error", "message": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
