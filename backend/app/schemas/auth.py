import re
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
)


UserRole = Literal[
    "customer",
    "support_agent",
    "admin",
]


class RegisterRequest(BaseModel):
    """
    Public Harbor registration.

    Role is intentionally absent.
    Every public signup becomes a customer.
    """

    full_name: str = Field(
        min_length=2,
        max_length=100,
    )

    age: int = Field(
        gt=0,
        le=120,
    )

    country: str = Field(
        min_length=2,
        max_length=100,
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    @field_validator("full_name")
    @classmethod
    def validate_full_name(
        cls,
        value: str,
    ) -> str:
        value = value.strip()

        if len(value) < 2:
            raise ValueError(
                "Full name must contain at least "
                "2 characters."
            )

        return value

    @field_validator("country")
    @classmethod
    def validate_country(
        cls,
        value: str,
    ) -> str:
        value = value.strip()

        if len(value) < 2:
            raise ValueError(
                "Country must contain at least "
                "2 characters."
            )

        return value

    @field_validator("password")
    @classmethod
    def validate_password(
        cls,
        value: str,
    ) -> str:
        if len(value) < 8:
            raise ValueError(
                "Password must be at least "
                "8 characters long."
            )

        if not re.search(
            r"[A-Za-z]",
            value,
        ):
            raise ValueError(
                "Password must contain at least "
                "one letter."
            )

        if not re.search(
            r"\d",
            value,
        ):
            raise ValueError(
                "Password must contain at least "
                "one number."
            )

        if not re.search(
            r"""[!@#$%^&*(),.?":{}|<>]""",
            value,
        ):
            raise ValueError(
                "Password must contain at least "
                "one special character."
            )

        return value


class RegisterResponse(BaseModel):
    message: str

    email: EmailStr

    verification_required: bool = True


class LoginRequest(BaseModel):
    email: EmailStr

    password: str


class UserResponse(BaseModel):
    id: UUID

    email: EmailStr

    full_name: str | None = None

    age: int | None = None

    country: str | None = None

    is_active: bool

    role: UserRole


class TokenResponse(BaseModel):
    access_token: str

    token_type: str = "bearer"

    expires_in: int

    user: UserResponse