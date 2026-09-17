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

from app.core.config import (
    get_settings,
)
from app.core.rate_limit import (
    limiter,
)
from app.db.supabase import (
    get_supabase_auth_client,
    get_supabase_client,
)
from app.dependencies.auth import (
    get_current_user,
)
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
)
from app.services.auth import (
    create_access_token,
    verify_password,
)


settings = get_settings()


router = APIRouter(
    prefix="/auth"
)


def normalize_email(
    email: str,
) -> str:
    return (
        email
        .strip()
        .lower()
    )


def get_harbor_user_by_email(
    email: str,
):
    supabase = (
        get_supabase_client()
    )

    response = (
        supabase
        .table("users")
        .select(
            "id,"
            "email,"
            "password_hash,"
            "full_name,"
            "age,"
            "country,"
            "is_active,"
            "role"
        )
        .eq(
            "email",
            email,
        )
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]


def authenticate_legacy_user(
    user: dict,
    password: str,
):
    """
    Support old Harbor bcrypt accounts during migration.
    """

    password_hash = (
        user.get(
            "password_hash"
        )
    )

    if not password_hash:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Invalid email or password."
            ),
        )

    if not verify_password(
        password,
        password_hash,
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Invalid email or password."
            ),
        )

    return user


def authenticate_supabase_user(
    email: str,
    password: str,
):
    """
    Authenticate a Supabase-managed Harbor user.

    Supabase handles both password verification and
    confirmed-email enforcement.
    """

    auth_client = (
        get_supabase_auth_client()
    )

    try:
        response = (
            auth_client
            .auth
            .sign_in_with_password(
                {
                    "email": email,
                    "password": password,
                }
            )
        )

    except Exception as exc:
        error_text = (
            str(exc).lower()
        )

        if (
            "email not confirmed"
            in error_text
            or "email_not_confirmed"
            in error_text
        ):
            raise HTTPException(
                status_code=(
                    status.HTTP_403_FORBIDDEN
                ),
                detail=(
                    "Please verify your email "
                    "before signing in."
                ),
            ) from exc

        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Invalid email or password."
            ),
        ) from exc

    if not response.user:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Invalid email or password."
            ),
        )

    return response.user


def authenticate_user(
    email: str,
    password: str,
):
    normalized_email = (
        normalize_email(
            email
        )
    )

    harbor_user = (
        get_harbor_user_by_email(
            normalized_email
        )
    )

    if not harbor_user:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Invalid email or password."
            ),
        )

    if not harbor_user[
        "is_active"
    ]:
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail=(
                "User account is inactive."
            ),
        )

    # Legacy account:
    # password still stored in Harbor.
    if harbor_user.get(
        "password_hash"
    ):
        return (
            authenticate_legacy_user(
                harbor_user,
                password,
            )
        )

    # Modern account:
    # password + email confirmation are owned by Supabase.
    auth_user = (
        authenticate_supabase_user(
            normalized_email,
            password,
        )
    )

    if (
        str(auth_user.id)
        != str(
            harbor_user["id"]
        )
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Authentication identity does "
                "not match Harbor profile."
            ),
        )

    return harbor_user


def build_token_response(
    user: dict,
) -> TokenResponse:
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
            age=user.get(
                "age"
            ),
            country=user.get(
                "country"
            ),
            is_active=user[
                "is_active"
            ],
            role=user["role"],
        ),
    )


@router.post(
    "/register",
    response_model=RegisterResponse,
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
    Public customer registration.

    Every public registration becomes customer.
    Staff email can never be registered publicly.
    """

    normalized_email = (
        normalize_email(
            str(
                payload.email
            )
        )
    )

    reserved_staff_email = (
        normalize_email(
            settings.staff_email
        )
    )

    # --------------------------------------------------------
    # Staff protection
    # --------------------------------------------------------

    if (
        normalized_email
        == reserved_staff_email
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail=(
                "This email address is reserved "
                "for Harbor staff."
            ),
        )

    service_client = (
        get_supabase_client()
    )

    # --------------------------------------------------------
    # Harbor duplicate profile check
    # --------------------------------------------------------

    existing_profile = (
        service_client
        .table("users")
        .select("id")
        .eq(
            "email",
            normalized_email,
        )
        .limit(1)
        .execute()
    )

    if existing_profile.data:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "An account with this email "
                "already exists."
            ),
        )

    # --------------------------------------------------------
    # Supabase Auth registration
    # --------------------------------------------------------

    auth_client = (
        get_supabase_auth_client()
    )

    verification_redirect = (
        settings
        .frontend_base_url
        .rstrip("/")
        + "/verify-email"
    )

    try:
        auth_response = (
            auth_client
            .auth
            .sign_up(
                {
                    "email": (
                        normalized_email
                    ),
                    "password": (
                        payload.password
                    ),
                    "options": {
                        "email_redirect_to": (
                            verification_redirect
                        ),
                        "data": {
                            "full_name": (
                                payload
                                .full_name
                                .strip()
                            ),
                            "age": (
                                payload.age
                            ),
                            "country": (
                                payload
                                .country
                                .strip()
                            ),
                        },
                    },
                }
            )
        )

    except Exception as exc:
        error_text = (
            str(exc)
        )

        if (
            "already registered"
            in error_text.lower()
        ):
            raise HTTPException(
                status_code=(
                    status.HTTP_409_CONFLICT
                ),
                detail=(
                    "An account with this email "
                    "already exists."
                ),
            ) from exc

        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "Unable to create account. "
                "Please check your information "
                "and try again."
            ),
        ) from exc

    auth_user = (
        auth_response.user
    )

    if not auth_user:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Supabase did not return "
                "a user account."
            ),
        )

    auth_user_id = str(
        auth_user.id
    )

    # --------------------------------------------------------
    # Create Harbor profile
    # --------------------------------------------------------

    try:
        profile_response = (
            service_client
            .table("users")
            .insert(
                {
                    "id": (
                        auth_user_id
                    ),
                    "email": (
                        normalized_email
                    ),

                    # New accounts use Supabase Auth.
                    "password_hash": None,

                    "full_name": (
                        payload
                        .full_name
                        .strip()
                    ),
                    "age": (
                        payload.age
                    ),
                    "country": (
                        payload
                        .country
                        .strip()
                    ),
                    "is_active": True,

                    # CRITICAL:
                    # public registration is always customer.
                    "role": "customer",
                }
            )
            .execute()
        )

    except Exception as exc:
        # Avoid orphan auth account if Harbor profile fails.
        try:
            (
                service_client
                .auth
                .admin
                .delete_user(
                    auth_user_id
                )
            )
        except Exception:
            pass

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Harbor could not create "
                "your customer profile."
            ),
        ) from exc

    if not profile_response.data:
        try:
            (
                service_client
                .auth
                .admin
                .delete_user(
                    auth_user_id
                )
            )
        except Exception:
            pass

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Harbor could not create "
                "your customer profile."
            ),
        )

    return RegisterResponse(
        message=(
            "Verification link sent. "
            "Please check your email."
        ),
        email=normalized_email,
        verification_required=True,
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
    user = authenticate_user(
        email=str(
            payload.email
        ),
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
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user.get(
            "full_name"
        ),
        age=current_user.get(
            "age"
        ),
        country=current_user.get(
            "country"
        ),
        is_active=current_user[
            "is_active"
        ],
        role=current_user["role"],
    )