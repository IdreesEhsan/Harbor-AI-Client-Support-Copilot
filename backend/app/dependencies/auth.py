import threading
from collections.abc import (
    Callable,
)
from time import monotonic
from typing import Any

from fastapi import (
    Depends,
    HTTPException,
    status,
)
from fastapi.security import (
    OAuth2PasswordBearer,
)
from jwt import (
    ExpiredSignatureError,
    InvalidTokenError,
)

from app.db.supabase import (
    get_supabase_client,
)
from app.schemas.auth import (
    UserRole,
)
from app.services.auth import (
    decode_access_token,
)


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token"
)


# ============================================================
# SHORT-LIVED AUTH PROFILE CACHE
# ============================================================

_USER_CACHE_TTL_SECONDS = 15.0


_user_cache: dict[
    str,
    tuple[
        float,
        dict[str, Any],
    ],
] = {}


_user_cache_lock = (
    threading.Lock()
)


def _get_cached_user(
    user_id: str,
) -> dict[str, Any] | None:
    """
    Return a recently-loaded Harbor user when available.

    JWT validation still happens for every request.

    Only the database profile lookup is cached.
    """

    now = (
        monotonic()
    )

    with _user_cache_lock:
        cached = (
            _user_cache.get(
                user_id
            )
        )

        if cached is None:
            return None

        cached_at, user = (
            cached
        )

        age = (
            now
            - cached_at
        )

        if (
            age
            >= _USER_CACHE_TTL_SECONDS
        ):
            _user_cache.pop(
                user_id,
                None,
            )

            return None

        return dict(
            user
        )


def _cache_user(
    user_id: str,
    user: dict[str, Any],
) -> None:
    """
    Cache one validated Harbor user for a very short period.
    """

    with _user_cache_lock:
        _user_cache[
            user_id
        ] = (
            monotonic(),
            dict(
                user
            ),
        )


def clear_current_user_cache(
    user_id: str | None = None,
) -> None:
    """
    Explicitly clear Harbor's short-lived user cache.

    This helper can later be called after administrative
    role/activation changes.

    Passing no user_id clears the entire cache.
    """

    with _user_cache_lock:
        if user_id is None:
            _user_cache.clear()
            return

        _user_cache.pop(
            str(
                user_id
            ),
            None,
        )


# ============================================================
# CURRENT USER
# ============================================================

def get_current_user(
    token: str = Depends(
        oauth2_scheme
    ),
):
    """
    Validate the Harbor JWT and load the authenticated user.

    Optimization:

        JWT validation:
            every request

        Supabase profile lookup:
            maximum once every 15 seconds per user

    This substantially reduces duplicate user-profile
    requests during page loading while preserving a short
    refresh window for role/account-state changes.
    """

    credentials_exception = (
        HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Could not validate credentials"
            ),
            headers={
                "WWW-Authenticate":
                    "Bearer"
            },
        )
    )


    # --------------------------------------------------------
    # 1. Validate JWT
    # --------------------------------------------------------

    try:
        payload = (
            decode_access_token(
                token
            )
        )

        user_id = (
            payload.get(
                "sub"
            )
        )

        if not user_id:
            raise (
                credentials_exception
            )

        user_id = str(
            user_id
        ).strip()

        if not user_id:
            raise (
                credentials_exception
            )


    except ExpiredSignatureError:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Token has expired"
            ),
            headers={
                "WWW-Authenticate":
                    "Bearer"
            },
        )


    except InvalidTokenError:
        raise (
            credentials_exception
        )


    # --------------------------------------------------------
    # 2. Check short-lived profile cache
    # --------------------------------------------------------

    user = (
        _get_cached_user(
            user_id
        )
    )


    # --------------------------------------------------------
    # 3. Load from Supabase only when cache misses
    # --------------------------------------------------------

    if user is None:
        supabase = (
            get_supabase_client()
        )

        response = (
            supabase
            .table("users")
            .select(
                (
                    "id,"
                    "email,"
                    "full_name,"
                    "age,"
                    "country,"
                    "is_active,"
                    "role"
                )
            )
            .eq(
                "id",
                user_id,
            )
            .limit(1)
            .execute()
        )

        if not response.data:
            raise (
                credentials_exception
            )

        user = (
            response.data[0]
        )

        _cache_user(
            user_id,
            user,
        )


    # --------------------------------------------------------
    # 4. Verify active account
    # --------------------------------------------------------

    if not user.get(
        "is_active"
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail=(
                "User account is inactive"
            ),
        )


    return user


# ============================================================
# ROLE AUTHORIZATION
# ============================================================

def require_roles(
    *allowed_roles: UserRole,
) -> Callable:
    """
    Restrict an endpoint to one or more Harbor roles.
    """

    if not allowed_roles:
        raise ValueError(
            (
                "At least one allowed role "
                "is required."
            )
        )


    def role_dependency(
        current_user=Depends(
            get_current_user
        ),
    ):
        user_role = (
            current_user.get(
                "role"
            )
        )


        if (
            user_role
            not in allowed_roles
        ):
            raise HTTPException(
                status_code=(
                    status.HTTP_403_FORBIDDEN
                ),
                detail=(
                    "You do not have permission "
                    "to perform this action."
                ),
            )


        return current_user


    return role_dependency