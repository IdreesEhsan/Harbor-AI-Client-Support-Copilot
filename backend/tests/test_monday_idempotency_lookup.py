from unittest.mock import patch

import pytest

from app.integrations.monday import (
    MondayAPIError,
    find_support_ticket_by_idempotency_key,
)


MONDAY_CONFIG = {
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


@patch(
    "app.integrations.monday._execute_graphql"
)
@patch(
    "app.integrations.monday."
    "get_monday_configuration"
)
def test_find_existing_item(
    mock_configuration,
    mock_execute,
):
    mock_configuration.return_value = (
        MONDAY_CONFIG.copy()
    )

    mock_execute.return_value = {
        "items_page_by_column_values": {
            "items": [
                {
                    "id": "2859744731",
                    "name": "Refund not received",
                }
            ]
        }
    }

    result = (
        find_support_ticket_by_idempotency_key(
            idempotency_key="idem-ticket-123"
        )
    )

    assert result == {
        "id": "2859744731",
        "name": "Refund not received",
    }

    call = mock_execute.call_args.kwargs

    assert (
        call["variables"]["boardId"]
        == "5031329288"
    )

    assert (
        call["variables"]["columnId"]
        == "text_mm77pmz5"
    )

    assert (
        call["variables"]["columnValues"]
        == ["idem-ticket-123"]
    )


@patch(
    "app.integrations.monday._execute_graphql"
)
@patch(
    "app.integrations.monday."
    "get_monday_configuration"
)
def test_missing_item_returns_none(
    mock_configuration,
    mock_execute,
):
    mock_configuration.return_value = (
        MONDAY_CONFIG.copy()
    )

    mock_execute.return_value = {
        "items_page_by_column_values": {
            "items": []
        }
    }

    result = (
        find_support_ticket_by_idempotency_key(
            idempotency_key="missing-key"
        )
    )

    assert result is None


@patch(
    "app.integrations.monday._execute_graphql"
)
@patch(
    "app.integrations.monday."
    "get_monday_configuration"
)
def test_duplicate_matches_fail_closed(
    mock_configuration,
    mock_execute,
):
    mock_configuration.return_value = (
        MONDAY_CONFIG.copy()
    )

    mock_execute.return_value = {
        "items_page_by_column_values": {
            "items": [
                {
                    "id": "111",
                    "name": "Ticket A",
                },
                {
                    "id": "222",
                    "name": "Ticket B",
                },
            ]
        }
    }

    with pytest.raises(
        MondayAPIError,
        match="Multiple Monday.com items",
    ):
        find_support_ticket_by_idempotency_key(
            idempotency_key="duplicate-key"
        )


@patch(
    "app.integrations.monday._execute_graphql"
)
@patch(
    "app.integrations.monday."
    "get_monday_configuration"
)
def test_invalid_search_payload_is_rejected(
    mock_configuration,
    mock_execute,
):
    mock_configuration.return_value = (
        MONDAY_CONFIG.copy()
    )

    mock_execute.return_value = {
        "items_page_by_column_values": {
            "items": "invalid"
        }
    }

    with pytest.raises(
        MondayAPIError,
        match="invalid item search result",
    ):
        find_support_ticket_by_idempotency_key(
            idempotency_key="idem-123"
        )


@pytest.mark.parametrize(
    "idempotency_key",
    [
        "",
        "   ",
    ],
)
def test_empty_idempotency_key_is_rejected(
    idempotency_key,
):
    with pytest.raises(
        ValueError,
        match="idempotency_key cannot be empty",
    ):
        find_support_ticket_by_idempotency_key(
            idempotency_key=idempotency_key
        )


def test_non_string_idempotency_key_is_rejected():
    with pytest.raises(
        TypeError,
        match="idempotency_key must be a string",
    ):
        find_support_ticket_by_idempotency_key(
            idempotency_key=123
        )