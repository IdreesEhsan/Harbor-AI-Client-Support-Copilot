from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import ExpiredSignatureError, InvalidTokenError

from app.db.supabase import get_supabase_client
from app.services.auth import decode_access_token
from collections.abc import Callable
from app.schemas.auth import UserRole


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token"
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={
            "WWW-Authenticate": "Bearer"
        },
    )

    try:
        payload = decode_access_token(token)

        user_id = payload.get("sub")

        if not user_id:
            raise credentials_exception

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    except InvalidTokenError:
        raise credentials_exception

    supabase = get_supabase_client()

    response = (
        supabase
        .table("users")
        .select(
            "id,email,full_name,is_active,role"
        )
        .eq("id", user_id)
        .limit(1)
        .execute()
    )

    if not response.data:
        raise credentials_exception

    user = response.data[0]

    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user

def require_roles(
    *allowed_roles: UserRole,
) -> Callable:
    """
    Create a FastAPI dependency that restricts an endpoint
    to one or more Harbor roles.

    Authentication and authorization remain separate:

    get_current_user()
        -> proves who the caller is

    require_roles(...)
        -> determines whether that caller may perform the
           protected operation
    """

    if not allowed_roles:
        raise ValueError(
            "At least one allowed role is required."
        )

    def role_dependency(
        current_user=Depends(
            get_current_user
        ),
    ):
        user_role = current_user.get(
            "role"
        )

        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You do not have permission "
                    "to perform this action."
                ),
            )

        return current_user

    return role_dependency