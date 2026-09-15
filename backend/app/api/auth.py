from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm

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


router = APIRouter(prefix="/auth")


def authenticate_user(
    email: str,
    password: str,
):
    """
    Authenticate a Harbor user using email and password.

    This helper is shared by the normal JSON login endpoint
    and the OAuth2-compatible Swagger login endpoint.

    The user's role is loaded from the database so Harbor can
    include the current authorization role in the login
    response and JWT.
    """

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
            email.lower(),
        )
        .limit(1)
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
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
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


def build_token_response(
    user: dict,
) -> TokenResponse:
    """
    Create the JWT response returned after successful
    authentication.

    The current Harbor role is included in both the JWT and
    the public user response.
    """

    access_token, expires_in = create_access_token(
        user_id=user["id"],
        email=user["email"],
        role=user["role"],
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
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: RegisterRequest,
):
    """
    Register a new Harbor customer.

    Public registration always assigns the customer role.
    Clients cannot choose support_agent or admin during
    registration.
    """

    supabase = get_supabase_client()

    existing_user = (
        supabase
        .table("users")
        .select("id")
        .eq(
            "email",
            payload.email.lower(),
        )
        .limit(1)
        .execute()
    )

    if existing_user.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "User with this email already exists"
            ),
        )

    password_hash = hash_password(
        payload.password
    )

    response = (
        supabase
        .table("users")
        .insert(
            {
                "email": payload.email.lower(),
                "password_hash": password_hash,
                "full_name": payload.full_name,
                # Public users must never be able to
                # self-assign privileged Harbor roles.
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
def login(
    payload: LoginRequest,
):
    """
    Normal JSON login endpoint.

    This endpoint is intended for clients such as Harbor's
    React frontend.
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
def oauth2_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """
    OAuth2-compatible login endpoint used by Swagger UI.

    OAuth2 calls the identity field "username". Harbor uses
    email addresses, so username is treated as the email.
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
    Return the currently authenticated Harbor user,
    including the user's current authorization role.
    """

    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user.get(
            "full_name"
        ),
        is_active=current_user["is_active"],
        role=current_user["role"],
    )