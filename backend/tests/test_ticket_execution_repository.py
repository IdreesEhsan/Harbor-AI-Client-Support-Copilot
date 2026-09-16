from unittest.mock import MagicMock, patch

import pytest

from app.repositories.ticket_repository import (
    mark_ticket_executed,
)


TICKET_ID = "ticket-123"
MONDAY_ITEM_ID = "monday-456"
CLAIM_ID = "550e8400-e29b-41d4-a716-446655440000"


def build_supabase_mock(
    response_data,
):
    """
    Build a chainable Supabase mock for execution
    finalization repository tests.
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
def test_mark_ticket_executed(
    mock_get_client,
):
    """
    The worker owning the execution claim may finalize the
    Monday synchronization.
    """

    synchronized_ticket = {
        "id": TICKET_ID,
        "approval_status": "approved",
        "status": "open",
        "monday_item_id": MONDAY_ITEM_ID,
        "external_status": "Open",
        "execution_claim_id": None,
        "execution_started_at": None,
    }

    client, table = build_supabase_mock(
        [synchronized_ticket]
    )

    mock_get_client.return_value = client

    result = mark_ticket_executed(
        ticket_id=TICKET_ID,
        monday_item_id=MONDAY_ITEM_ID,
        execution_claim_id=CLAIM_ID,
    )

    assert result == synchronized_ticket

    client.table.assert_called_once_with(
        "support_tickets"
    )

    payload = table.update.call_args.args[0]

    assert payload["monday_item_id"] == MONDAY_ITEM_ID
    assert payload["status"] == "open"
    assert payload["external_status"] == "Open"
    assert payload["last_synced_at"]
    assert payload["updated_at"]
    assert payload["failure_reason"] is None

    # Successful finalization releases the lease.
    assert payload["execution_claim_id"] is None
    assert payload["execution_started_at"] is None


@patch(
    "app.repositories.ticket_repository."
    "get_supabase_client"
)
def test_execution_requires_executing_state(
    mock_get_client,
):
    """
    Finalization must only operate on a ticket currently in
    the executing workflow state.
    """

    client, table = build_supabase_mock([])

    mock_get_client.return_value = client

    result = mark_ticket_executed(
        ticket_id=TICKET_ID,
        monday_item_id=MONDAY_ITEM_ID,
        execution_claim_id=CLAIM_ID,
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
        "executing",
    ) in eq_calls


@patch(
    "app.repositories.ticket_repository."
    "get_supabase_client"
)
def test_execution_requires_matching_claim(
    mock_get_client,
):
    """
    Finalization must include the worker's execution claim.

    This conditional filter prevents stale workers from
    completing a newer worker's execution attempt.
    """

    client, table = build_supabase_mock([])

    mock_get_client.return_value = client

    result = mark_ticket_executed(
        ticket_id=TICKET_ID,
        monday_item_id=MONDAY_ITEM_ID,
        execution_claim_id=CLAIM_ID,
    )

    assert result is None

    eq_calls = [
        call.args
        for call in table.eq.call_args_list
    ]

    assert (
        "execution_claim_id",
        CLAIM_ID,
    ) in eq_calls


@patch(
    "app.repositories.ticket_repository."
    "get_supabase_client"
)
def test_execution_requires_no_existing_monday_item(
    mock_get_client,
):
    """
    Finalization must not overwrite an existing Monday
    synchronization.
    """

    client, table = build_supabase_mock([])

    mock_get_client.return_value = client

    result = mark_ticket_executed(
        ticket_id=TICKET_ID,
        monday_item_id=MONDAY_ITEM_ID,
        execution_claim_id=CLAIM_ID,
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
def test_failed_finalization_returns_none(
    mock_get_client,
):
    """
    A failed conditional update must be represented as None.
    """

    client, _ = build_supabase_mock([])

    mock_get_client.return_value = client

    result = mark_ticket_executed(
        ticket_id=TICKET_ID,
        monday_item_id=MONDAY_ITEM_ID,
        execution_claim_id=CLAIM_ID,
    )

    assert result is None


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
    with pytest.raises(
        ValueError,
        match="ticket_id cannot be empty",
    ):
        mark_ticket_executed(
            ticket_id=ticket_id,
            monday_item_id=MONDAY_ITEM_ID,
            execution_claim_id=CLAIM_ID,
        )


@pytest.mark.parametrize(
    "monday_item_id",
    [
        "",
        "   ",
    ],
)
def test_empty_monday_item_id_is_rejected(
    monday_item_id,
):
    with pytest.raises(
        ValueError,
        match="monday_item_id cannot be empty",
    ):
        mark_ticket_executed(
            ticket_id=TICKET_ID,
            monday_item_id=monday_item_id,
            execution_claim_id=CLAIM_ID,
        )


@pytest.mark.parametrize(
    "execution_claim_id",
    [
        "",
        "   ",
    ],
)
def test_empty_execution_claim_id_is_rejected(
    execution_claim_id,
):
    """
    Harbor must never attempt claim-less finalization.
    """

    with pytest.raises(
        ValueError,
        match="execution_claim_id cannot be empty",
    ):
        mark_ticket_executed(
            ticket_id=TICKET_ID,
            monday_item_id=MONDAY_ITEM_ID,
            execution_claim_id=execution_claim_id,
        )


def test_non_string_ticket_id_is_rejected():
    with pytest.raises(
        TypeError,
        match="ticket_id must be a string",
    ):
        mark_ticket_executed(
            ticket_id=123,
            monday_item_id=MONDAY_ITEM_ID,
            execution_claim_id=CLAIM_ID,
        )


def test_non_string_monday_item_id_is_rejected():
    with pytest.raises(
        TypeError,
        match="monday_item_id must be a string",
    ):
        mark_ticket_executed(
            ticket_id=TICKET_ID,
            monday_item_id=123,
            execution_claim_id=CLAIM_ID,
        )


def test_non_string_execution_claim_id_is_rejected():
    with pytest.raises(
        TypeError,
        match="execution_claim_id must be a string",
    ):
        mark_ticket_executed(
            ticket_id=TICKET_ID,
            monday_item_id=MONDAY_ITEM_ID,
            execution_claim_id=123,
        )