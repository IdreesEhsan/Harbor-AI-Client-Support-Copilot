from fastapi import APIRouter, HTTPException, status

from app.db.supabase import get_supabase_client
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
from fastapi import Depends
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/auth")


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: RegisterRequest):
    supabase = get_supabase_client()

    existing_user = (
        supabase
        .table("users")
        .select("id")
        .eq("email", payload.email.lower())
        .limit(1)
        .execute()
    )

    if existing_user.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    password_hash = hash_password(payload.password)

    response = (
        supabase
        .table("users")
        .insert(
            {
                "email": payload.email.lower(),
                "password_hash": password_hash,
                "full_name": payload.full_name,
            }
        )
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create user",
        )

    user = response.data[0]

    return UserResponse(
        id=user["id"],
        email=user["email"],
        full_name=user.get("full_name"),
        is_active=user["is_active"],
    )

@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(payload: LoginRequest):
    supabase = get_supabase_client()

    response = (
        supabase
        .table("users")
        .select(
            "id,email,password_hash,full_name,is_active"
        )
        .eq("email", payload.email.lower())
        .limit(1)
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    user = response.data[0]

    if not verify_password(
        payload.password,
        user["password_hash"],
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    access_token, expires_in = create_access_token(
        user_id=user["id"],
        email=user["email"],
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=expires_in,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            full_name=user.get("full_name"),
            is_active=user["is_active"],
        ),
    )

@router.get(
    "/me",
    response_model=UserResponse,
)
def get_me(
    current_user=Depends(get_current_user),
):
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user.get("full_name"),
        is_active=current_user["is_active"],
    )