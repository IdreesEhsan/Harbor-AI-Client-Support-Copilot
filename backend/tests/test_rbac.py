from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.dependencies.auth import require_roles
from app.schemas.auth import (
    RegisterRequest,
    UserResponse,
)


def test_register_request_has_no_role_field():
    """
    Public registration must not expose role assignment.
    """

    assert (
        "role"
        not in RegisterRequest.model_fields
    )


def test_user_response_accepts_customer():
    user = UserResponse(
        id="550e8400-e29b-41d4-a716-446655440000",
        email="customer@example.com",
        full_name="Customer",
        is_active=True,
        role="customer",
    )

    assert user.role == "customer"


def test_user_response_accepts_support_agent():
    user = UserResponse(
        id="550e8400-e29b-41d4-a716-446655440000",
        email="agent@example.com",
        full_name="Agent",
        is_active=True,
        role="support_agent",
    )

    assert user.role == "support_agent"


def test_user_response_accepts_admin():
    user = UserResponse(
        id="550e8400-e29b-41d4-a716-446655440000",
        email="admin@example.com",
        full_name="Admin",
        is_active=True,
        role="admin",
    )

    assert user.role == "admin"


def test_user_response_rejects_unknown_role():
    with pytest.raises(ValueError):
        UserResponse(
            id=(
                "550e8400-e29b-41d4-"
                "a716-446655440000"
            ),
            email="user@example.com",
            full_name="User",
            is_active=True,
            role="superuser",
        )


def test_require_roles_rejects_empty_configuration():
    with pytest.raises(
        ValueError,
        match="At least one allowed role",
    ):
        require_roles()


def test_require_roles_allows_support_agent():
    dependency = require_roles(
        "support_agent",
        "admin",
    )

    user = {
        "id": "user-1",
        "role": "support_agent",
    }

    result = dependency(
        current_user=user
    )

    assert result == user


def test_require_roles_allows_admin():
    dependency = require_roles(
        "support_agent",
        "admin",
    )

    user = {
        "id": "user-1",
        "role": "admin",
    }

    result = dependency(
        current_user=user
    )

    assert result == user


def test_require_roles_blocks_customer():
    dependency = require_roles(
        "support_agent",
        "admin",
    )

    with pytest.raises(
        HTTPException
    ) as exc_info:
        dependency(
            current_user={
                "id": "user-1",
                "role": "customer",
            }
        )

    assert (
        exc_info.value.status_code
        == 403
    )


def test_require_roles_blocks_missing_role():
    dependency = require_roles(
        "support_agent",
        "admin",
    )

    with pytest.raises(
        HTTPException
    ) as exc_info:
        dependency(
            current_user={
                "id": "user-1",
            }
        )

    assert (
        exc_info.value.status_code
        == 403
    )