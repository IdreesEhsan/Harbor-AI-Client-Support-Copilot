from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.services.ticket_execution_service import (
    TicketExecutionClaimError,
    claim_authorized_ticket,
)
from app.tickets.execution_lease import (
    InvalidExecutionLeaseError,
)


TICKET_ID = "ticket-123"

OLD_CLAIM_ID = (
    "550e8400-e29b-41d4-a716-446655440000"
)

NEW_CLAIM_ID = (
    "123e4567-e89b-12d3-a456-426614174000"
)


def build_executing_ticket(
    *,
    started_at: datetime,
) -> dict:
    """
    Build a persisted executing ticket representing an
    existing worker's execution lease.
    """

    return {
        "id": TICKET_ID,
        "approval_status": "approved",
        "status": "executing",
        "execution_claim_id": OLD_CLAIM_ID,
        "execution_started_at": (
            started_at.isoformat()
        ),
        "monday_item_id": None,
    }


@patch(
    "app.services.ticket_execution_service."
    "recover_stale_execution_claim"
)
@patch(
    "app.services.ticket_execution_service."
    "is_execution_lease_stale"
)
def test_active_execution_lease_is_not_stolen(
    mock_is_stale,
    mock_recover,
):
    """
    An active execution lease belongs to another worker and
    must never be replaced.
    """

    ticket = build_executing_ticket(
        started_at=(
            datetime.now(timezone.utc)
            - timedelta(seconds=60)
        )
    )

    mock_is_stale.return_value = False

    with pytest.raises(
        TicketExecutionClaimError,
        match="currently being executed",
    ):
        claim_authorized_ticket(
            ticket=ticket
        )

    mock_is_stale.assert_called_once_with(
        execution_started_at=(
            ticket["execution_started_at"]
        )
    )

    mock_recover.assert_not_called()


@patch(
    "app.services.ticket_execution_service."
    "recover_stale_execution_claim"
)
@patch(
    "app.services.ticket_execution_service."
    "is_execution_lease_stale"
)
def test_stale_execution_lease_is_recovered(
    mock_is_stale,
    mock_recover,
):
    """
    A stale lease may be replaced through the repository's
    atomic compare-and-swap operation.
    """

    ticket = build_executing_ticket(
        started_at=(
            datetime.now(timezone.utc)
            - timedelta(minutes=10)
        )
    )

    recovered_ticket = {
        **ticket,
        "execution_claim_id": (
            NEW_CLAIM_ID
        ),
        "execution_started_at": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
    }

    mock_is_stale.return_value = True
    mock_recover.return_value = (
        recovered_ticket
    )

    result = claim_authorized_ticket(
        ticket=ticket
    )

    assert result == recovered_ticket

    mock_is_stale.assert_called_once_with(
        execution_started_at=(
            ticket["execution_started_at"]
        )
    )

    mock_recover.assert_called_once_with(
        ticket_id=TICKET_ID,
        previous_claim_id=(
            OLD_CLAIM_ID
        ),
    )


@patch(
    "app.services.ticket_execution_service."
    "recover_stale_execution_claim"
)
@patch(
    "app.services.ticket_execution_service."
    "is_execution_lease_stale"
)
def test_lost_stale_recovery_race_fails_closed(
    mock_is_stale,
    mock_recover,
):
    """
    A stale lease alone does not grant ownership.

    If the compare-and-swap update returns no row, another
    recovery worker may have acquired the lease first.
    """

    ticket = build_executing_ticket(
        started_at=(
            datetime.now(timezone.utc)
            - timedelta(minutes=10)
        )
    )

    mock_is_stale.return_value = True
    mock_recover.return_value = None

    with pytest.raises(
        TicketExecutionClaimError,
        match="could not be recovered",
    ):
        claim_authorized_ticket(
            ticket=ticket
        )

    mock_is_stale.assert_called_once_with(
        execution_started_at=(
            ticket["execution_started_at"]
        )
    )

    mock_recover.assert_called_once_with(
        ticket_id=TICKET_ID,
        previous_claim_id=(
            OLD_CLAIM_ID
        ),
    )


@patch(
    "app.services.ticket_execution_service."
    "recover_stale_execution_claim"
)
@patch(
    "app.services.ticket_execution_service."
    "is_execution_lease_stale"
)
def test_missing_claim_id_fails_before_lease_check(
    mock_is_stale,
    mock_recover,
):
    """
    Harbor cannot reason about ownership when an executing
    ticket has no persisted execution claim ID.
    """

    ticket = build_executing_ticket(
        started_at=(
            datetime.now(timezone.utc)
        )
    )

    ticket["execution_claim_id"] = None

    with pytest.raises(
        TicketExecutionClaimError,
        match="valid execution claim ID",
    ):
        claim_authorized_ticket(
            ticket=ticket
        )

    mock_is_stale.assert_not_called()
    mock_recover.assert_not_called()


@patch(
    "app.services.ticket_execution_service."
    "recover_stale_execution_claim"
)
@patch(
    "app.services.ticket_execution_service."
    "is_execution_lease_stale"
)
def test_blank_claim_id_fails_before_lease_check(
    mock_is_stale,
    mock_recover,
):
    """
    A whitespace-only execution claim ID is invalid and must
    not reach stale-lease evaluation.
    """

    ticket = build_executing_ticket(
        started_at=(
            datetime.now(timezone.utc)
        )
    )

    ticket["execution_claim_id"] = "   "

    with pytest.raises(
        TicketExecutionClaimError,
        match="valid execution claim ID",
    ):
        claim_authorized_ticket(
            ticket=ticket
        )

    mock_is_stale.assert_not_called()
    mock_recover.assert_not_called()


@patch(
    "app.services.ticket_execution_service."
    "recover_stale_execution_claim"
)
@patch(
    "app.services.ticket_execution_service."
    "is_execution_lease_stale"
)
def test_missing_started_at_fails_before_recovery(
    mock_is_stale,
    mock_recover,
):
    """
    Harbor must not recover an executing ticket when the
    lease start time is missing.
    """

    ticket = build_executing_ticket(
        started_at=(
            datetime.now(timezone.utc)
        )
    )

    ticket["execution_started_at"] = None

    with pytest.raises(
        TicketExecutionClaimError,
        match="valid execution start timestamp",
    ):
        claim_authorized_ticket(
            ticket=ticket
        )

    mock_is_stale.assert_not_called()
    mock_recover.assert_not_called()


@patch(
    "app.services.ticket_execution_service."
    "recover_stale_execution_claim"
)
@patch(
    "app.services.ticket_execution_service."
    "is_execution_lease_stale"
)
def test_blank_started_at_fails_before_recovery(
    mock_is_stale,
    mock_recover,
):
    """
    A whitespace-only execution start timestamp must fail
    before stale recovery is attempted.
    """

    ticket = build_executing_ticket(
        started_at=(
            datetime.now(timezone.utc)
        )
    )

    ticket["execution_started_at"] = "   "

    with pytest.raises(
        TicketExecutionClaimError,
        match="valid execution start timestamp",
    ):
        claim_authorized_ticket(
            ticket=ticket
        )

    mock_is_stale.assert_not_called()
    mock_recover.assert_not_called()


@patch(
    "app.services.ticket_execution_service."
    "recover_stale_execution_claim"
)
@patch(
    "app.services.ticket_execution_service."
    "is_execution_lease_stale"
)
def test_invalid_lease_metadata_fails_closed(
    mock_is_stale,
    mock_recover,
):
    """
    Invalid persisted lease metadata must not lead to an
    ownership takeover.
    """

    ticket = build_executing_ticket(
        started_at=(
            datetime.now(timezone.utc)
        )
    )

    mock_is_stale.side_effect = (
        InvalidExecutionLeaseError(
            "Invalid lease."
        )
    )

    with pytest.raises(
        TicketExecutionClaimError,
        match="invalid execution lease metadata",
    ):
        claim_authorized_ticket(
            ticket=ticket
        )

    mock_recover.assert_not_called()


@patch(
    "app.services.ticket_execution_service."
    "recover_stale_execution_claim"
)
@patch(
    "app.services.ticket_execution_service."
    "is_execution_lease_stale"
)
def test_type_error_from_lease_validation_fails_closed(
    mock_is_stale,
    mock_recover,
):
    """
    Unexpected lease input type failures must also fail
    closed before atomic takeover.
    """

    ticket = build_executing_ticket(
        started_at=(
            datetime.now(timezone.utc)
        )
    )

    mock_is_stale.side_effect = TypeError(
        "Invalid lease type."
    )

    with pytest.raises(
        TicketExecutionClaimError,
        match="invalid execution lease metadata",
    ):
        claim_authorized_ticket(
            ticket=ticket
        )

    mock_recover.assert_not_called()


@patch(
    "app.services.ticket_execution_service."
    "claim_ticket_for_execution"
)
def test_approved_ticket_uses_normal_claim_path(
    mock_claim,
):
    """
    First-time execution must continue using the normal
    approved -> executing atomic claim.
    """

    approved_ticket = {
        "id": TICKET_ID,
        "approval_status": "approved",
        "status": "approved",
        "monday_item_id": None,
    }

    claimed_ticket = {
        **approved_ticket,
        "status": "executing",
        "execution_claim_id": (
            NEW_CLAIM_ID
        ),
        "execution_started_at": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
    }

    mock_claim.return_value = (
        claimed_ticket
    )

    result = claim_authorized_ticket(
        ticket=approved_ticket
    )

    assert result == claimed_ticket

    mock_claim.assert_called_once_with(
        TICKET_ID
    )


@patch(
    "app.services.ticket_execution_service."
    "claim_ticket_for_execution"
)
def test_failed_normal_claim_fails_closed(
    mock_claim,
):
    """
    Losing the normal approved -> executing race must stop
    execution before any external operation.
    """

    approved_ticket = {
        "id": TICKET_ID,
        "approval_status": "approved",
        "status": "approved",
        "monday_item_id": None,
    }

    mock_claim.return_value = None

    with pytest.raises(
        TicketExecutionClaimError,
        match="could not be claimed",
    ):
        claim_authorized_ticket(
            ticket=approved_ticket
        )

    mock_claim.assert_called_once_with(
        TICKET_ID
    )


def test_missing_ticket_id_is_rejected():
    """
    An execution claim cannot be established without the
    persisted Harbor ticket ID.
    """

    ticket = {
        "approval_status": "approved",
        "status": "approved",
        "monday_item_id": None,
    }

    with pytest.raises(
        TicketExecutionClaimError,
        match="valid ticket ID",
    ):
        claim_authorized_ticket(
            ticket=ticket
        )


def test_unexpected_status_is_not_claimable():
    """
    Defensive validation prevents unsupported workflow
    states from acquiring execution ownership.
    """

    ticket = {
        "id": TICKET_ID,
        "approval_status": "approved",
        "status": "open",
    }

    with pytest.raises(
        TicketExecutionClaimError,
        match="not in a claimable",
    ):
        claim_authorized_ticket(
            ticket=ticket
        )