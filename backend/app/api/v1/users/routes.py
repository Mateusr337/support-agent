from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.responses import CONFLICT_RESPONSE, merge_responses, VALIDATION_ERROR_RESPONSE
from app.api.v1.dependencies import get_user_service
from app.api.v1.users.schemas import CreateUserRequest, UserResponse
from app.services.user_service import UserAlreadyExistsError, UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse,
    responses=merge_responses(
        CONFLICT_RESPONSE,
        VALIDATION_ERROR_RESPONSE,
    ),
)
def create_user(
    body: CreateUserRequest,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    try:
        user = service.create_user(
            email=body.email,
            name=body.name,
            password=body.password,
        )
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return UserResponse.model_validate(user)
