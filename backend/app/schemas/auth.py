from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
)


UserRole = Literal[
    "customer",
    "support_agent",
    "admin",
]


class RegisterRequest(BaseModel):
    """
    Public Harbor registration request.

    Role is intentionally absent. Public users must not be
    able to assign themselves privileged roles.
    """

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    full_name: str | None = Field(
        default=None,
        max_length=100,
    )


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str | None
    is_active: bool
    role: UserRole


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse