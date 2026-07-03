from pydantic import BaseModel, EmailStr, Field

from app.api.v1.users.schemas import UserResponse


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
