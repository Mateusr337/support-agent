from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.auth.dependencies import get_current_user
from app.api.v1.auth.schemas import LoginRequest, LoginResponse
from app.api.v1.dependencies import get_user_service
from app.api.v1.responses import (
    merge_responses,
    UNAUTHORIZED_RESPONSE,
    VALIDATION_ERROR_RESPONSE,
)
from app.api.v1.users.schemas import UserResponse
from app.core.security import create_access_token
from app.models.user import User
from app.services.user_service import InvalidCredentialsError, UserService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    response_model=LoginResponse,
    responses=merge_responses(
        UNAUTHORIZED_RESPONSE,
        VALIDATION_ERROR_RESPONSE,
    ),
)
def login(
    body: LoginRequest,
    service: UserService = Depends(get_user_service),
) -> LoginResponse:
    try:
        user = service.authenticate_user(email=body.email, password=body.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    access_token = create_access_token(user_id=user.id, email=user.email)

    return LoginResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    response_model=UserResponse,
    responses=UNAUTHORIZED_RESPONSE,
)
def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
