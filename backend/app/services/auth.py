from datetime import (
    datetime,
    timedelta,
    timezone,
)
from typing import Any

import bcrypt
import jwt

from app.core.config import (
    get_settings,
)


settings = get_settings()


def hash_password(
    password: str,
) -> str:
    """
    Legacy Harbor password hashing.

    Retained temporarily for existing accounts that
    were created before Supabase Auth migration.
    """

    password_bytes = (
        password.encode(
            "utf-8"
        )
    )

    hashed_password = (
        bcrypt.hashpw(
            password_bytes,
            bcrypt.gensalt(),
        )
    )

    return hashed_password.decode(
        "utf-8"
    )


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """
    Verify legacy Harbor bcrypt credentials.
    """

    return bcrypt.checkpw(
        plain_password.encode(
            "utf-8"
        ),
        hashed_password.encode(
            "utf-8"
        ),
    )


def create_access_token(
    user_id: str,
    email: str,
    role: str,
) -> tuple[str, int]:
    """
    Create Harbor's application JWT.

    Supabase Auth authenticates the password/email.
    Harbor's JWT remains responsible for application
    authentication and RBAC.
    """

    expires_minutes = (
        settings
        .jwt_access_token_expire_minutes
    )

    now = datetime.now(
        timezone.utc
    )

    expire = (
        now
        + timedelta(
            minutes=expires_minutes
        )
    )

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "exp": expire,
        "iat": now,
    }

    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=(
            settings.jwt_algorithm
        ),
    )

    return (
        token,
        expires_minutes * 60,
    )


def decode_access_token(
    token: str,
) -> dict[str, Any]:
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[
            settings.jwt_algorithm
        ],
    )