from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.users.schemas import CreateUserRequest, UserResponse
from app.core.database import get_db
from app.services.user_service import UserAlreadyExistsError, UserService

router = APIRouter(prefix="/users", tags=["users"])


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse,
    responses={
        status.HTTP_409_CONFLICT: {
            "description": "A user with this email already exists",
        },
    },
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
