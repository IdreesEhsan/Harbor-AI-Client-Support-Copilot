from unittest.mock import patch

import pytest

from app.integrations.monday import (
    MondayAPIError,
)
from app.services.ticket_execution_service import (
    TicketExecutionClaimError,
    TicketExecutionPersistenceError,
    TicketExternalExecutionError,
    execute_approved_ticket,
)


EXECUTION_CLAIM_ID = (
    "550e8400-e29b-41d4-a716-446655440000"
)

APPROVED_TICKET = {
    "id": "ticket-123",
    "user_id": "user-123",
    "conversation_id": "conversation-123",
    "title": "Refund not received",
    "description": (
        "The customer has not received the expected refund."
    ),
    "severity": "medium",
    "status": "approved",
    "approval_status": "approved",
    "idempotency_key": "harbor-idempotency-123",
    "monday_item_id": None,
    "execution_claim_id": None,
    "execution_started_at": None,
}


def build_claimed_ticket():
    """
    Return the persisted representation Harbor receives after
    winning the atomic execution claim.

    The important lifecycle transition is:

        approved
            ↓
        executing
        + execution_claim_id
        + execution_started_at

    The execution claim ID represents ownership of this
    specific execution attempt.
    """

    return {
        **APPROVED_TICKET,
        "status": "executing",
        "execution_claim_id": (
            EXECUTION_CLAIM_ID
        ),
        "execution_started_at": (
            "2026-09-15T12:00:00+00:00"
        ),
    }


@patch(
    "app.services.ticket_execution_service."
    "mark_ticket_executed"
)
@patch(
    "app.services.ticket_execution_service."
    "create_support_ticket_item"
)
@patch(
    "app.services.ticket_execution_service."
    "find_support_ticket_by_idempotency_key"
)
@patch(
    "app.services.ticket_execution_service."
    "claim_ticket_for_execution"
)
@patch(
    "app.services.ticket_execution_service."
    "authorize_ticket_execution"
)
def test_missing_external_item_creates_and_persists(
    mock_authorize,
    mock_claim,
    mock_find_monday,
    mock_create_monday,
    mock_mark_executed,
):
    """
    When Monday contains no matching idempotency key, the
    worker holding Harbor's execution claim should create one
    external item and persist it using the same claim ID.
    """

    mock_authorize.return_value = (
        APPROVED_TICKET.copy()
    )

    mock_claim.return_value = (
        build_claimed_ticket()
    )

    mock_find_monday.return_value = None

    mock_create_monday.return_value = {
        "id": "2859744731",
        "name": "Refund not received",
    }

    synchronized_ticket = {
        **APPROVED_TICKET,
        "status": "open",
        "monday_item_id": "2859744731",
        "external_status": "Open",
        "execution_claim_id": None,
        "execution_started_at": None,
    }

    mock_mark_executed.return_value = (
        synchronized_ticket
    )

    result = execute_approved_ticket(
        ticket_id="ticket-123"
    )

    assert result == synchronized_ticket

    mock_authorize.assert_called_once_with(
        ticket_id="ticket-123"
    )

    mock_claim.assert_called_once_with(
        "ticket-123"
    )

    mock_find_monday.assert_called_once_with(
        idempotency_key=(
            "harbor-idempotency-123"
        )
    )

    mock_create_monday.assert_called_once_with(
        title="Refund not received",
        description=(
            "The customer has not received "
            "the expected refund."
        ),
        severity="medium",
        harbor_ticket_id="ticket-123",
        idempotency_key=(
            "harbor-idempotency-123"
        ),
    )

    # The exact claim ID returned by the atomic database
    # claim must be presented during finalization.
    mock_mark_executed.assert_called_once_with(
        ticket_id="ticket-123",
        monday_item_id="2859744731",
        execution_claim_id=(
            EXECUTION_CLAIM_ID
        ),
    )


@patch(
    "app.services.ticket_execution_service."
    "mark_ticket_executed"
)
@patch(
    "app.services.ticket_execution_service."
    "create_support_ticket_item"
)
@patch(
    "app.services.ticket_execution_service."
    "find_support_ticket_by_idempotency_key"
)
@patch(
    "app.services.ticket_execution_service."
    "claim_ticket_for_execution"
)
@patch(
    "app.services.ticket_execution_service."
    "authorize_ticket_execution"
)
def test_existing_external_item_is_reused(
    mock_authorize,
    mock_claim,
    mock_find_monday,
    mock_create_monday,
    mock_mark_executed,
):
    """
    A previously created Monday item should be recovered
    instead of creating a duplicate.

    Recovery finalization must still prove ownership using
    the current execution claim.
    """

    mock_authorize.return_value = (
        APPROVED_TICKET.copy()
    )

    mock_claim.return_value = (
        build_claimed_ticket()
    )

    mock_find_monday.return_value = {
        "id": "existing-789",
        "name": "Refund not received",
    }

    synchronized_ticket = {
        **APPROVED_TICKET,
        "status": "open",
        "monday_item_id": "existing-789",
        "external_status": "Open",
        "execution_claim_id": None,
        "execution_started_at": None,
    }

    mock_mark_executed.return_value = (
        synchronized_ticket
    )

    result = execute_approved_ticket(
        ticket_id="ticket-123"
    )

    assert result == synchronized_ticket

    mock_claim.assert_called_once_with(
        "ticket-123"
    )

    mock_create_monday.assert_not_called()

    mock_mark_executed.assert_called_once_with(
        ticket_id="ticket-123",
        monday_item_id="existing-789",
        execution_claim_id=(
            EXECUTION_CLAIM_ID
        ),
    )


@patch(
    "app.services.ticket_execution_service."
    "mark_ticket_executed"
)
@patch(
    "app.services.ticket_execution_service."
    "create_support_ticket_item"
)
@patch(
    "app.services.ticket_execution_service."
    "find_support_ticket_by_idempotency_key"
)
@patch(
    "app.services.ticket_execution_service."
    "claim_ticket_for_execution"
)
@patch(
    "app.services.ticket_execution_service."
    "authorize_ticket_execution"
)
def test_lookup_failure_fails_closed(
    mock_authorize,
    mock_claim,
    mock_find_monday,
    mock_create_monday,
    mock_mark_executed,
):
    """
    A failed idempotency lookup must never be interpreted as
    proof that the Monday item does not exist.
    """

    mock_authorize.return_value = (
        APPROVED_TICKET.copy()
    )

    mock_claim.return_value = (
        build_claimed_ticket()
    )

    mock_find_monday.side_effect = (
        MondayAPIError(
            "Monday lookup failed."
        )
    )

    with pytest.raises(
        TicketExternalExecutionError,
        match="safely synchronized",
    ):
        execute_approved_ticket(
            ticket_id="ticket-123"
        )

    mock_create_monday.assert_not_called()
    mock_mark_executed.assert_not_called()


@patch(
    "app.services.ticket_execution_service."
    "mark_ticket_executed"
)
@patch(
    "app.services.ticket_execution_service."
    "create_support_ticket_item"
)
@patch(
    "app.services.ticket_execution_service."
    "find_support_ticket_by_idempotency_key"
)
@patch(
    "app.services.ticket_execution_service."
    "claim_ticket_for_execution"
)
@patch(
    "app.services.ticket_execution_service."
    "authorize_ticket_execution"
)
def test_creation_failure_does_not_mark_executed(
    mock_authorize,
    mock_claim,
    mock_find_monday,
    mock_create_monday,
    mock_mark_executed,
):
    """
    If lookup succeeds but Monday creation fails, Harbor must
    not record external execution as successful.
    """

    mock_authorize.return_value = (
        APPROVED_TICKET.copy()
    )

    mock_claim.return_value = (
        build_claimed_ticket()
    )

    mock_find_monday.return_value = None

    mock_create_monday.side_effect = (
        MondayAPIError(
            "Monday creation failed."
        )
    )

    with pytest.raises(
        TicketExternalExecutionError,
        match="safely synchronized",
    ):
        execute_approved_ticket(
            ticket_id="ticket-123"
        )

    mock_mark_executed.assert_not_called()


@patch(
    "app.services.ticket_execution_service."
    "mark_ticket_executed"
)
@patch(
    "app.services.ticket_execution_service."
    "create_support_ticket_item"
)
@patch(
    "app.services.ticket_execution_service."
    "find_support_ticket_by_idempotency_key"
)
@patch(
    "app.services.ticket_execution_service."
    "claim_ticket_for_execution"
)
@patch(
    "app.services.ticket_execution_service."
    "authorize_ticket_execution"
)
def test_missing_monday_item_id_is_rejected(
    mock_authorize,
    mock_claim,
    mock_find_monday,
    mock_create_monday,
    mock_mark_executed,
):
    """
    A Monday result cannot be synchronized without a valid
    external item ID.
    """

    mock_authorize.return_value = (
        APPROVED_TICKET.copy()
    )

    mock_claim.return_value = (
        build_claimed_ticket()
    )

    mock_find_monday.return_value = None

    mock_create_monday.return_value = {
        "name": "Refund not received",
    }

    with pytest.raises(
        TicketExternalExecutionError,
        match="valid item ID",
    ):
        execute_approved_ticket(
            ticket_id="ticket-123"
        )

    mock_mark_executed.assert_not_called()


@patch(
    "app.services.ticket_execution_service."
    "mark_ticket_executed"
)
@patch(
    "app.services.ticket_execution_service."
    "create_support_ticket_item"
)
@patch(
    "app.services.ticket_execution_service."
    "find_support_ticket_by_idempotency_key"
)
@patch(
    "app.services.ticket_execution_service."
    "claim_ticket_for_execution"
)
@patch(
    "app.services.ticket_execution_service."
    "authorize_ticket_execution"
)
def test_persistence_failure_is_distinguished(
    mock_authorize,
    mock_claim,
    mock_find_monday,
    mock_create_monday,
    mock_mark_executed,
):
    """
    Monday success followed by Harbor persistence failure
    remains a distinct partial-success state.
    """

    mock_authorize.return_value = (
        APPROVED_TICKET.copy()
    )

    mock_claim.return_value = (
        build_claimed_ticket()
    )

    mock_find_monday.return_value = None

    mock_create_monday.return_value = {
        "id": "2859744731",
        "name": "Refund not received",
    }

    mock_mark_executed.return_value = None

    with pytest.raises(
        TicketExecutionPersistenceError,
        match="could not persist",
    ):
        execute_approved_ticket(
            ticket_id="ticket-123"
        )

    mock_mark_executed.assert_called_once_with(
        ticket_id="ticket-123",
        monday_item_id="2859744731",
        execution_claim_id=(
            EXECUTION_CLAIM_ID
        ),
    )


@patch(
    "app.services.ticket_execution_service."
    "mark_ticket_executed"
)
@patch(
    "app.services.ticket_execution_service."
    "create_support_ticket_item"
)
@patch(
    "app.services.ticket_execution_service."
    "find_support_ticket_by_idempotency_key"
)
@patch(
    "app.services.ticket_execution_service."
    "claim_ticket_for_execution"
)
@patch(
    "app.services.ticket_execution_service."
    "authorize_ticket_execution"
)
def test_recovered_item_persistence_failure_does_not_create(
    mock_authorize,
    mock_claim,
    mock_find_monday,
    mock_create_monday,
    mock_mark_executed,
):
    """
    Even if Harbor fails to persist a recovered Monday item,
    it must never attempt another create operation.
    """

    mock_authorize.return_value = (
        APPROVED_TICKET.copy()
    )

    mock_claim.return_value = (
        build_claimed_ticket()
    )

    mock_find_monday.return_value = {
        "id": "existing-789",
        "name": "Refund not received",
    }

    mock_mark_executed.return_value = None

    with pytest.raises(
        TicketExecutionPersistenceError,
        match="could not persist",
    ):
        execute_approved_ticket(
            ticket_id="ticket-123"
        )

    mock_create_monday.assert_not_called()

    mock_mark_executed.assert_called_once_with(
        ticket_id="ticket-123",
        monday_item_id="existing-789",
        execution_claim_id=(
            EXECUTION_CLAIM_ID
        ),
    )


@patch(
    "app.services.ticket_execution_service."
    "mark_ticket_executed"
)
@patch(
    "app.services.ticket_execution_service."
    "create_support_ticket_item"
)
@patch(
    "app.services.ticket_execution_service."
    "find_support_ticket_by_idempotency_key"
)
@patch(
    "app.services.ticket_execution_service."
    "claim_ticket_for_execution"
)
@patch(
    "app.services.ticket_execution_service."
    "authorize_ticket_execution"
)
def test_authorization_failure_stops_all_external_calls(
    mock_authorize,
    mock_claim,
    mock_find_monday,
    mock_create_monday,
    mock_mark_executed,
):
    """
    Nothing may be claimed or sent to Monday when Harbor's
    authorization boundary rejects execution.
    """

    mock_authorize.side_effect = (
        TicketExternalExecutionError(
            "Authorization failed."
        )
    )

    with pytest.raises(
        TicketExternalExecutionError,
        match="Authorization failed",
    ):
        execute_approved_ticket(
            ticket_id="ticket-123"
        )

    mock_claim.assert_not_called()
    mock_find_monday.assert_not_called()
    mock_create_monday.assert_not_called()
    mock_mark_executed.assert_not_called()


@patch(
    "app.services.ticket_execution_service."
    "mark_ticket_executed"
)
@patch(
    "app.services.ticket_execution_service."
    "create_support_ticket_item"
)
@patch(
    "app.services.ticket_execution_service."
    "find_support_ticket_by_idempotency_key"
)
@patch(
    "app.services.ticket_execution_service."
    "claim_ticket_for_execution"
)
@patch(
    "app.services.ticket_execution_service."
    "authorize_ticket_execution"
)
def test_missing_persisted_idempotency_key_fails_closed(
    mock_authorize,
    mock_claim,
    mock_find_monday,
    mock_create_monday,
    mock_mark_executed,
):
    """
    Harbor must not execute externally if the claimed ticket
    unexpectedly lacks an idempotency key.
    """

    mock_authorize.return_value = (
        APPROVED_TICKET.copy()
    )

    claimed_ticket = (
        build_claimed_ticket()
    )

    claimed_ticket["idempotency_key"] = ""

    mock_claim.return_value = (
        claimed_ticket
    )

    with pytest.raises(
        TicketExternalExecutionError,
        match="valid idempotency key",
    ):
        execute_approved_ticket(
            ticket_id="ticket-123"
        )

    mock_find_monday.assert_not_called()
    mock_create_monday.assert_not_called()
    mock_mark_executed.assert_not_called()


@patch(
    "app.services.ticket_execution_service."
    "mark_ticket_executed"
)
@patch(
    "app.services.ticket_execution_service."
    "create_support_ticket_item"
)
@patch(
    "app.services.ticket_execution_service."
    "find_support_ticket_by_idempotency_key"
)
@patch(
    "app.services.ticket_execution_service."
    "claim_ticket_for_execution"
)
@patch(
    "app.services.ticket_execution_service."
    "authorize_ticket_execution"
)
def test_failed_atomic_claim_stops_all_monday_calls(
    mock_authorize,
    mock_claim,
    mock_find_monday,
    mock_create_monday,
    mock_mark_executed,
):
    """
    A worker that loses Harbor's atomic execution claim must
    stop before any Monday.com read or write.

    This remains Harbor's central concurrency guarantee.
    """

    mock_authorize.return_value = (
        APPROVED_TICKET.copy()
    )

    # None represents a failed conditional database update.
    # Another worker may have already moved the ticket from
    # approved to executing.
    mock_claim.return_value = None

    with pytest.raises(
        TicketExecutionClaimError,
        match="could not be claimed",
    ):
        execute_approved_ticket(
            ticket_id="ticket-123"
        )

    mock_claim.assert_called_once_with(
        "ticket-123"
    )

    mock_find_monday.assert_not_called()
    mock_create_monday.assert_not_called()
    mock_mark_executed.assert_not_called()


@patch(
    "app.services.ticket_execution_service."
    "mark_ticket_executed"
)
@patch(
    "app.services.ticket_execution_service."
    "create_support_ticket_item"
)
@patch(
    "app.services.ticket_execution_service."
    "find_support_ticket_by_idempotency_key"
)
@patch(
    "app.services.ticket_execution_service."
    "claim_ticket_for_execution"
)
@patch(
    "app.services.ticket_execution_service."
    "authorize_ticket_execution"
)
def test_missing_execution_claim_id_stops_before_monday(
    mock_authorize,
    mock_claim,
    mock_find_monday,
    mock_create_monday,
    mock_mark_executed,
):
    """
    A claimed ticket without execution ownership metadata
    must fail closed before any Monday operation.

    This protects Harbor from performing an external write
    that it would not later be authorized to finalize.
    """

    mock_authorize.return_value = (
        APPROVED_TICKET.copy()
    )

    claimed_ticket = (
        build_claimed_ticket()
    )

    claimed_ticket["execution_claim_id"] = None

    mock_claim.return_value = (
        claimed_ticket
    )

    with pytest.raises(
        TicketExecutionClaimError,
        match="valid execution claim ID",
    ):
        execute_approved_ticket(
            ticket_id="ticket-123"
        )

    mock_find_monday.assert_not_called()
    mock_create_monday.assert_not_called()
    mock_mark_executed.assert_not_called()


@patch(
    "app.services.ticket_execution_service."
    "mark_ticket_executed"
)
@patch(
    "app.services.ticket_execution_service."
    "create_support_ticket_item"
)
@patch(
    "app.services.ticket_execution_service."
    "find_support_ticket_by_idempotency_key"
)
@patch(
    "app.services.ticket_execution_service."
    "claim_ticket_for_execution"
)
@patch(
    "app.services.ticket_execution_service."
    "authorize_ticket_execution"
)
def test_empty_execution_claim_id_stops_before_monday(
    mock_authorize,
    mock_claim,
    mock_find_monday,
    mock_create_monday,
    mock_mark_executed,
):
    """
    Whitespace-only execution ownership is invalid and must
    stop before external access.
    """

    mock_authorize.return_value = (
        APPROVED_TICKET.copy()
    )

    claimed_ticket = (
        build_claimed_ticket()
    )

    claimed_ticket["execution_claim_id"] = "   "

    mock_claim.return_value = (
        claimed_ticket
    )

    with pytest.raises(
        TicketExecutionClaimError,
        match="valid execution claim ID",
    ):
        execute_approved_ticket(
            ticket_id="ticket-123"
        )

    mock_find_monday.assert_not_called()
    mock_create_monday.assert_not_called()
    mock_mark_executed.assert_not_called()