from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from app.repositories.ticket_repository import (
    claim_ticket_for_execution,
)


def build_supabase_mock(
    response_data,
):
    """
    Build a chainable Supabase client mock for atomic
    execution-claim repository tests.
    """

    client = MagicMock()
    table = MagicMock()

    client.table.return_value = table
    table.update.return_value = table
    table.eq.return_value = table
    table.is_.return_value = table

    response = MagicMock()
    response.data = response_data

    table.execute.return_value = response

    return client, table


@patch(
    "app.repositories.ticket_repository."
    "get_supabase_client"
)
def test_successful_claim_sets_execution_metadata(
    mock_get_client,
):
    """
    A successful claim must move the ticket into executing
    and assign execution ownership metadata.
    """

    claimed_ticket = {
        "id": "ticket-123",
        "approval_status": "approved",
        "status": "executing",
        "execution_claim_id": (
            "550e8400-e29b-41d4-a716-446655440000"
        ),
        "execution_started_at": (
            "2026-09-15T12:00:00+00:00"
        ),
        "monday_item_id": None,
    }

    client, table = build_supabase_mock(
        [claimed_ticket]
    )

    mock_get_client.return_value = client

    result = claim_ticket_for_execution(
        "ticket-123"
    )

    assert result == claimed_ticket

    client.table.assert_called_once_with(
        "support_tickets"
    )

    payload = (
        table.update.call_args.args[0]
    )

    assert (
        payload["status"]
        == "executing"
    )

    assert payload["execution_claim_id"]
    assert payload["execution_started_at"]
    assert payload["updated_at"]

    # The generated execution claim must be a valid UUID.
    UUID(
        payload["execution_claim_id"]
    )


@patch(
    "app.repositories.ticket_repository."
    "get_supabase_client"
)
def test_claim_requires_approved_state(
    mock_get_client,
):
    """
    Only an approved workflow state may transition into
    executing.
    """

    client, table = build_supabase_mock(
        []
    )

    mock_get_client.return_value = client

    result = claim_ticket_for_execution(
        "ticket-123"
    )

    assert result is None

    eq_calls = [
        call.args
        for call in table.eq.call_args_list
    ]

    assert (
        "approval_status",
        "approved",
    ) in eq_calls

    assert (
        "status",
        "approved",
    ) in eq_calls


@patch(
    "app.repositories.ticket_repository."
    "get_supabase_client"
)
def test_claim_requires_no_existing_monday_item(
    mock_get_client,
):
    """
    A ticket already linked to Monday.com must not receive a
    new execution claim.
    """

    client, table = build_supabase_mock(
        []
    )

    mock_get_client.return_value = client

    result = claim_ticket_for_execution(
        "ticket-123"
    )

    assert result is None

    table.is_.assert_called_once_with(
        "monday_item_id",
        "null",
    )


@patch(
    "app.repositories.ticket_repository."
    "get_supabase_client"
)
def test_failed_conditional_claim_returns_none(
    mock_get_client,
):
    """
    No returned row means this worker lost the atomic
    execution claim.
    """

    client, _ = build_supabase_mock(
        []
    )

    mock_get_client.return_value = client

    result = claim_ticket_for_execution(
        "ticket-123"
    )

    assert result is None


@patch(
    "app.repositories.ticket_repository."
    "get_supabase_client"
)
def test_separate_claim_attempts_generate_unique_ids(
    mock_get_client,
):
    """
    Independent execution attempts must never reuse the same
    claim identifier.
    """

    client, table = build_supabase_mock(
        []
    )

    mock_get_client.return_value = client

    claim_ticket_for_execution(
        "ticket-123"
    )

    first_payload = (
        table.update.call_args.args[0]
    )

    first_claim_id = (
        first_payload[
            "execution_claim_id"
        ]
    )

    # Reset recorded calls before making another independent
    # execution attempt.
    table.reset_mock()

    # reset_mock() also clears the configured chaining
    # behavior, so rebuild it.
    table.update.return_value = table
    table.eq.return_value = table
    table.is_.return_value = table

    response = MagicMock()
    response.data = []

    table.execute.return_value = response

    claim_ticket_for_execution(
        "ticket-123"
    )

    second_payload = (
        table.update.call_args.args[0]
    )

    second_claim_id = (
        second_payload[
            "execution_claim_id"
        ]
    )

    assert (
        first_claim_id
        != second_claim_id
    )

    UUID(first_claim_id)
    UUID(second_claim_id)


@patch(
    "app.repositories.ticket_repository."
    "get_supabase_client"
)
def test_claim_records_same_timestamp_for_start_and_update(
    mock_get_client,
):
    """
    The initial execution lease timestamp and updated_at
    should describe the same atomic claim event.
    """

    client, table = build_supabase_mock(
        []
    )

    mock_get_client.return_value = client

    claim_ticket_for_execution(
        "ticket-123"
    )

    payload = (
        table.update.call_args.args[0]
    )

    assert (
        payload["execution_started_at"]
        == payload["updated_at"]
    )


@pytest.mark.parametrize(
    "ticket_id",
    [
        "",
        "   ",
    ],
)
def test_empty_ticket_id_is_rejected(
    ticket_id,
):
    """
    Empty ticket IDs must never reach Supabase.
    """

    with pytest.raises(
        ValueError,
        match="ticket_id cannot be empty",
    ):
        claim_ticket_for_execution(
            ticket_id
        )


def test_non_string_ticket_id_is_rejected():
    """
    Ticket IDs must use Harbor's expected string
    representation.
    """

    with pytest.raises(
        TypeError,
        match="ticket_id must be a string",
    ):
        claim_ticket_for_execution(
            123
        )