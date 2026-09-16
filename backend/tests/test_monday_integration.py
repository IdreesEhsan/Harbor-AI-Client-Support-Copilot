import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.integrations.monday import (
    MondayAPIError,
    MondayConfigurationError,
    create_support_ticket_item,
    get_monday_configuration,
    normalize_severity,
)


def build_settings():
    """
    Build Monday settings matching Harbor's real board
    structure without exposing a real API token.
    """

    settings = MagicMock()

    settings.monday_api_token = "test-token"
    settings.monday_api_url = (
        "https://api.monday.com/v2"
    )

    settings.monday_board_id = "5031329288"
    settings.monday_group_id = "topics"

    settings.monday_harbor_ticket_id_column_id = (
        "text_mm77n14z"
    )
    settings.monday_status_column_id = (
        "color_mm77cf6n"
    )
    settings.monday_idempotency_key_column_id = (
        "text_mm77pmz5"
    )
    settings.monday_description_column_id = (
        "text_mm77drt"
    )
    settings.monday_severity_column_id = (
        "color_mm77eh43"
    )

    return settings


@patch(
    "app.integrations.monday.get_settings"
)
def test_get_monday_configuration(
    mock_get_settings,
):
    mock_get_settings.return_value = (
        build_settings()
    )

    result = get_monday_configuration()

    assert result["board_id"] == (
        "5031329288"
    )

    assert result["group_id"] == "topics"

    assert result[
        "status_column_id"
    ] == "color_mm77cf6n"

    assert result[
        "severity_column_id"
    ] == "color_mm77eh43"


@patch(
    "app.integrations.monday.get_settings"
)
def test_incomplete_configuration_is_rejected(
    mock_get_settings,
):
    settings = build_settings()
    settings.monday_api_token = None

    mock_get_settings.return_value = settings

    with pytest.raises(
        MondayConfigurationError,
        match="api_token",
    ):
        get_monday_configuration()


@pytest.mark.parametrize(
    ("harbor_value", "monday_label"),
    [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ],
)
def test_normalize_severity(
    harbor_value,
    monday_label,
):
    assert (
        normalize_severity(
            harbor_value
        )
        == monday_label
    )


def test_invalid_severity_is_rejected():
    with pytest.raises(
        ValueError,
        match="Unsupported ticket severity",
    ):
        normalize_severity(
            "emergency"
        )


@patch(
    "app.integrations.monday.httpx.post"
)
@patch(
    "app.integrations.monday."
    "get_monday_configuration"
)
def test_create_support_ticket_item_uses_real_columns(
    mock_configuration,
    mock_post,
):
    """
    Verify Harbor constructs the Monday mutation using the
    actual configured board column IDs.
    """

    mock_configuration.return_value = {
        "api_token": "test-token",
        "api_url": "https://api.monday.com/v2",
        "board_id": "5031329288",
        "group_id": "topics",
        "harbor_ticket_id_column_id": (
            "text_mm77n14z"
        ),
        "status_column_id": (
            "color_mm77cf6n"
        ),
        "idempotency_key_column_id": (
            "text_mm77pmz5"
        ),
        "description_column_id": (
            "text_mm77drt"
        ),
        "severity_column_id": (
            "color_mm77eh43"
        ),
    }

    response = MagicMock()

    response.json.return_value = {
        "data": {
            "create_item": {
                "id": "987654321",
                "name": "Refund not received",
            }
        }
    }

    mock_post.return_value = response

    result = create_support_ticket_item(
        title="Refund not received",
        description=(
            "Customer requires human assistance."
        ),
        severity="high",
        harbor_ticket_id="HTID-TEST",
        idempotency_key="IDEMP-TEST",
    )

    assert result == {
        "id": "987654321",
        "name": "Refund not received",
    }

    mock_post.assert_called_once()

    request = mock_post.call_args.kwargs

    assert (
        request["json"]["variables"]["boardId"]
        == "5031329288"
    )

    assert (
        request["json"]["variables"]["groupId"]
        == "topics"
    )

    column_values = json.loads(
        request["json"]["variables"][
            "columnValues"
        ]
    )

    assert column_values[
        "text_mm77n14z"
    ] == "HTID-TEST"

    assert column_values[
        "color_mm77cf6n"
    ] == {
        "label": "Open"
    }

    assert column_values[
        "text_mm77pmz5"
    ] == "IDEMP-TEST"

    assert column_values[
        "color_mm77eh43"
    ] == {
        "label": "High"
    }


@patch(
    "app.integrations.monday.httpx.post"
)
@patch(
    "app.integrations.monday."
    "get_monday_configuration"
)
def test_http_failure_raises_safe_error(
    mock_configuration,
    mock_post,
):
    mock_configuration.return_value = {
        "api_token": "test-token",
        "api_url": "https://api.monday.com/v2",
        "board_id": "5031329288",
        "group_id": "topics",
        "harbor_ticket_id_column_id": "ticket",
        "status_column_id": "status",
        "idempotency_key_column_id": "key",
        "description_column_id": "description",
        "severity_column_id": "severity",
    }

    mock_post.side_effect = (
        httpx.RequestError(
            "network unavailable"
        )
    )

    with pytest.raises(
        MondayAPIError,
        match="request failed",
    ):
        create_support_ticket_item(
            title="Refund issue",
            description="Needs support.",
            severity="medium",
            harbor_ticket_id="ticket-1",
            idempotency_key="key-1",
        )


@patch(
    "app.integrations.monday.httpx.post"
)
@patch(
    "app.integrations.monday."
    "get_monday_configuration"
)
def test_graphql_error_is_rejected(
    mock_configuration,
    mock_post,
):
    mock_configuration.return_value = {
        "api_token": "test-token",
        "api_url": "https://api.monday.com/v2",
        "board_id": "5031329288",
        "group_id": "topics",
        "harbor_ticket_id_column_id": "ticket",
        "status_column_id": "status",
        "idempotency_key_column_id": "key",
        "description_column_id": "description",
        "severity_column_id": "severity",
    }

    response = MagicMock()

    response.json.return_value = {
        "errors": [
            {
                "message": "Invalid column value"
            }
        ]
    }

    mock_post.return_value = response

    with pytest.raises(
        MondayAPIError,
        match="GraphQL errors",
    ):
        create_support_ticket_item(
            title="Refund issue",
            description="Needs support.",
            severity="medium",
            harbor_ticket_id="ticket-1",
            idempotency_key="key-1",
        )


def test_empty_title_is_rejected():
    with pytest.raises(
        ValueError,
        match="title cannot be empty",
    ):
        create_support_ticket_item(
            title="   ",
            description="Needs support.",
            severity="medium",
            harbor_ticket_id="ticket-1",
            idempotency_key="key-1",
        )


def test_empty_description_is_rejected():
    with pytest.raises(
        ValueError,
        match="description cannot be empty",
    ):
        create_support_ticket_item(
            title="Refund issue",
            description="   ",
            severity="medium",
            harbor_ticket_id="ticket-1",
            idempotency_key="key-1",
        )