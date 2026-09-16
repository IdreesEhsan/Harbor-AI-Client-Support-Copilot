from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.security import (
    OAuth2PasswordRequestForm,
)

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db.supabase import get_supabase_client
from app.dependencies.auth import get_current_user
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth import (
    create_access_token,
    hash_password,
    verify_password,
)


settings = get_settings()


router = APIRouter(
    prefix="/auth"
)


def authenticate_user(
    email: str,
    password: str,
):
    """
    Authenticate a Harbor user using email and password.

    Used by both React JSON login and Swagger OAuth2 login.
    """

    email = email.strip().lower()

    if not email:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail="Invalid email or password",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    supabase = get_supabase_client()

    response = (
        supabase
        .table("users")
        .select(
            "id,email,password_hash,"
            "full_name,is_active,role"
        )
        .eq(
            "email",
            email,
        )
        .limit(1)
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail="Invalid email or password",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    user = response.data[0]

    if not verify_password(
        password,
        user["password_hash"],
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail="Invalid email or password",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    if not user["is_active"]:
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail="User account is inactive",
        )

    return user


def build_token_response(
    user: dict,
) -> TokenResponse:
    """
    Create Harbor's JWT authentication response.
    """

    access_token, expires_in = (
        create_access_token(
            user_id=user["id"],
            email=user["email"],
            role=user["role"],
        )
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=expires_in,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            full_name=user.get(
                "full_name"
            ),
            is_active=user["is_active"],
            role=user["role"],
        ),
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=(
        status.HTTP_201_CREATED
    ),
)
@limiter.limit(
    settings.auth_rate_limit
)
def register(
    request: Request,
    payload: RegisterRequest,
):
    """
    Register a Harbor customer.

    Public registration is deliberately restricted to the
    customer role. Privileged roles cannot be self-assigned.
    """

    supabase = (
        get_supabase_client()
    )

    normalized_email = (
        payload.email.strip().lower()
    )

    existing_user = (
        supabase
        .table("users")
        .select("id")
        .eq(
            "email",
            normalized_email,
        )
        .limit(1)
        .execute()
    )

    if existing_user.data:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "User with this email "
                "already exists"
            ),
        )

    password_hash = (
        hash_password(
            payload.password
        )
    )

    response = (
        supabase
        .table("users")
        .insert(
            {
                "email": (
                    normalized_email
                ),
                "password_hash": (
                    password_hash
                ),
                "full_name": (
                    payload.full_name
                ),
                "role": "customer",
            }
        )
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail="Could not create user",
        )

    user = response.data[0]

    return UserResponse(
        id=user["id"],
        email=user["email"],
        full_name=user.get(
            "full_name"
        ),
        is_active=user["is_active"],
        role=user["role"],
    )


@router.post(
    "/login",
    response_model=TokenResponse,
)
@limiter.limit(
    settings.auth_rate_limit
)
def login(
    request: Request,
    payload: LoginRequest,
):
    """
    JSON login endpoint used by Harbor's React frontend.

    Rate limiting reduces brute-force login attempts.
    """

    user = authenticate_user(
        email=payload.email,
        password=payload.password,
    )

    return build_token_response(
        user
    )


@router.post(
    "/token",
    response_model=TokenResponse,
)
@limiter.limit(
    settings.auth_rate_limit
)
def oauth2_login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """
    OAuth2-compatible authentication endpoint used by
    Swagger UI.

    OAuth2 calls the identity field 'username'; Harbor treats
    it as the user's email address.
    """

    user = authenticate_user(
        email=form_data.username,
        password=form_data.password,
    )

    return build_token_response(
        user
    )


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_me(
    current_user=Depends(
        get_current_user
    ),
):
    """
    Return the currently authenticated Harbor user.
    """

    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user.get(
            "full_name"
        ),
        is_active=current_user[
            "is_active"
        ],
        role=current_user["role"],
    )