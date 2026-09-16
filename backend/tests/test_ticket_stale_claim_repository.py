from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from app.repositories.ticket_repository import (
    recover_stale_execution_claim,
)


TICKET_ID = "ticket-123"

PREVIOUS_CLAIM_ID = (
    "550e8400-e29b-41d4-a716-446655440000"
)


def build_supabase_mock(
    response_data,
):
    """
    Build a chainable Supabase mock for stale execution
    claim recovery tests.
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
def test_stale_claim_is_replaced_with_new_lease(
    mock_get_client,
):
    """
    Successful recovery must keep the ticket executing while
    replacing the old execution ownership metadata.
    """

    recovered_ticket = {
        "id": TICKET_ID,
        "approval_status": "approved",
        "status": "executing",
        "execution_claim_id": (
            "123e4567-e89b-12d3-a456-426614174000"
        ),
        "execution_started_at": (
            "2026-09-15T12:10:00+00:00"
        ),
        "monday_item_id": None,
    }

    client, table = build_supabase_mock(
        [recovered_ticket]
    )

    mock_get_client.return_value = client

    result = recover_stale_execution_claim(
        ticket_id=TICKET_ID,
        previous_claim_id=(
            PREVIOUS_CLAIM_ID
        ),
    )

    assert result == recovered_ticket

    payload = (
        table.update.call_args.args[0]
    )

    assert payload["status"] == "executing"

    new_claim_id = (
        payload["execution_claim_id"]
    )

    assert new_claim_id
    assert (
        new_claim_id
        != PREVIOUS_CLAIM_ID
    )

    UUID(new_claim_id)

    assert payload["execution_started_at"]
    assert (
        payload["execution_started_at"]
        == payload["updated_at"]
    )


@patch(
    "app.repositories.ticket_repository."
    "get_supabase_client"
)
def test_recovery_requires_previous_claim_match(
    mock_get_client,
):
    """
    Compare-and-swap recovery must match the exact claim the
    recovery worker previously inspected.
    """

    client, table = build_supabase_mock(
        []
    )

    mock_get_client.return_value = client

    result = recover_stale_execution_claim(
        ticket_id=TICKET_ID,
        previous_claim_id=(
            PREVIOUS_CLAIM_ID
        ),
    )

    assert result is None

    eq_calls = [
        call.args
        for call in table.eq.call_args_list
    ]

    assert (
        "execution_claim_id",
        PREVIOUS_CLAIM_ID,
    ) in eq_calls


@patch(
    "app.repositories.ticket_repository."
    "get_supabase_client"
)
def test_recovery_requires_executing_state(
    mock_get_client,
):
    """
    Recovery must never claim an approved, open, rejected,
    or otherwise non-executing ticket.
    """

    client, table = build_supabase_mock(
        []
    )

    mock_get_client.return_value = client

    recover_stale_execution_claim(
        ticket_id=TICKET_ID,
        previous_claim_id=(
            PREVIOUS_CLAIM_ID
        ),
    )

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
def test_recovery_requires_no_monday_item(
    mock_get_client,
):
    """
    A ticket already synchronized to Monday must never have
    its execution lease recovered.
    """

    client, table = build_supabase_mock(
        []
    )

    mock_get_client.return_value = client

    recover_stale_execution_claim(
        ticket_id=TICKET_ID,
        previous_claim_id=(
            PREVIOUS_CLAIM_ID
        ),
    )

    table.is_.assert_called_once_with(
        "monday_item_id",
        "null",
    )


@patch(
    "app.repositories.ticket_repository."
    "get_supabase_client"
)
def test_failed_atomic_recovery_returns_none(
    mock_get_client,
):
    """
    No returned row means this recovery worker did not gain
    execution ownership.
    """

    client, _ = build_supabase_mock(
        []
    )

    mock_get_client.return_value = client

    result = recover_stale_execution_claim(
        ticket_id=TICKET_ID,
        previous_claim_id=(
            PREVIOUS_CLAIM_ID
        ),
    )

    assert result is None


@patch(
    "app.repositories.ticket_repository."
    "get_supabase_client"
)
def test_separate_recoveries_generate_unique_claim_ids(
    mock_get_client,
):
    """
    Independent recovery attempts must generate independent
    ownership tokens.
    """

    client, table = build_supabase_mock(
        []
    )

    mock_get_client.return_value = client

    recover_stale_execution_claim(
        ticket_id=TICKET_ID,
        previous_claim_id=(
            PREVIOUS_CLAIM_ID
        ),
    )

    first_payload = (
        table.update.call_args.args[0]
    )

    first_claim_id = (
        first_payload["execution_claim_id"]
    )

    table.reset_mock()

    table.update.return_value = table
    table.eq.return_value = table
    table.is_.return_value = table

    response = MagicMock()
    response.data = []
    table.execute.return_value = response

    recover_stale_execution_claim(
        ticket_id=TICKET_ID,
        previous_claim_id=(
            PREVIOUS_CLAIM_ID
        ),
    )

    second_payload = (
        table.update.call_args.args[0]
    )

    second_claim_id = (
        second_payload["execution_claim_id"]
    )

    assert (
        first_claim_id
        != second_claim_id
    )

    UUID(first_claim_id)
    UUID(second_claim_id)


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
        recover_stale_execution_claim(
            ticket_id=ticket_id,
            previous_claim_id=(
                PREVIOUS_CLAIM_ID
            ),
        )


@pytest.mark.parametrize(
    "previous_claim_id",
    [
        "",
        "   ",
    ],
)
def test_empty_previous_claim_id_is_rejected(
    previous_claim_id,
):
    with pytest.raises(
        ValueError,
        match="previous_claim_id cannot be empty",
    ):
        recover_stale_execution_claim(
            ticket_id=TICKET_ID,
            previous_claim_id=(
                previous_claim_id
            ),
        )


def test_non_string_ticket_id_is_rejected():
    with pytest.raises(
        TypeError,
        match="ticket_id must be a string",
    ):
        recover_stale_execution_claim(
            ticket_id=123,
            previous_claim_id=(
                PREVIOUS_CLAIM_ID
            ),
        )


def test_non_string_previous_claim_id_is_rejected():
    with pytest.raises(
        TypeError,
        match="previous_claim_id must be a string",
    ):
        recover_stale_execution_claim(
            ticket_id=TICKET_ID,
            previous_claim_id=123,
        )