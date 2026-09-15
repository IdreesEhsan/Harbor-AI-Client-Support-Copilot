from unittest.mock import patch
from uuid import UUID, uuid4

import pytest

from app.services.ticket_service import (
    TicketAlreadyDecidedError,
    TicketNotFoundError,
    decide_ticket_approval,
    review_ticket,
)


@patch(
    "app.services.ticket_service."
    "get_ticket_for_review"
)
def test_review_ticket_returns_ticket(
    mock_get_ticket,
):
    ticket_id = str(uuid4())

    ticket = {
        "id": ticket_id,
        "status": "pending_approval",
        "approval_status": "pending",
    }

    mock_get_ticket.return_value = ticket

    result = review_ticket(
        ticket_id=ticket_id
    )

    assert result == ticket

    mock_get_ticket.assert_called_once_with(
        ticket_id
    )


@patch(
    "app.services.ticket_service."
    "get_ticket_for_review"
)
def test_review_ticket_raises_when_missing(
    mock_get_ticket,
):
    mock_get_ticket.return_value = None

    with pytest.raises(
        TicketNotFoundError,
        match="Support ticket was not found",
    ):
        review_ticket(
            ticket_id=str(uuid4())
        )


@patch(
    "app.services.ticket_service."
    "approve_ticket"
)
@patch(
    "app.services.ticket_service."
    "get_ticket_for_review"
)
def test_approve_pending_ticket(
    mock_get_ticket,
    mock_approve_ticket,
):
    ticket_id = str(uuid4())
    reviewer_id = str(uuid4())

    mock_get_ticket.return_value = {
        "id": ticket_id,
        "status": "pending_approval",
        "approval_status": "pending",
    }

    mock_approve_ticket.return_value = {
        "id": ticket_id,
        "status": "approved",
        "approval_status": "approved",
        "approved_by": reviewer_id,
        "approved_at": (
            "2026-09-15T10:00:00+00:00"
        ),
    }

    result = decide_ticket_approval(
        ticket_id=ticket_id,
        reviewer_id=reviewer_id,
        approved=True,
    )

    assert result.ticket_id == UUID(
        ticket_id
    )

    assert result.status == "approved"

    assert (
        result.approval_status
        == "approved"
    )

    assert result.approved_by == UUID(
        reviewer_id
    )

    mock_approve_ticket.assert_called_once_with(
        ticket_id=ticket_id,
        approved_by=reviewer_id,
    )


@patch(
    "app.services.ticket_service."
    "reject_ticket"
)
@patch(
    "app.services.ticket_service."
    "get_ticket_for_review"
)
def test_reject_pending_ticket(
    mock_get_ticket,
    mock_reject_ticket,
):
    ticket_id = str(uuid4())
    reviewer_id = str(uuid4())

    mock_get_ticket.return_value = {
        "id": ticket_id,
        "status": "pending_approval",
        "approval_status": "pending",
    }

    mock_reject_ticket.return_value = {
        "id": ticket_id,
        "status": "rejected",
        "approval_status": "rejected",
        "approved_by": reviewer_id,
        "approved_at": (
            "2026-09-15T10:00:00+00:00"
        ),
    }

    result = decide_ticket_approval(
        ticket_id=ticket_id,
        reviewer_id=reviewer_id,
        approved=False,
    )

    assert result.ticket_id == UUID(
        ticket_id
    )

    assert result.status == "rejected"

    assert (
        result.approval_status
        == "rejected"
    )

    assert result.approved_by == UUID(
        reviewer_id
    )

    mock_reject_ticket.assert_called_once_with(
        ticket_id=ticket_id,
        rejected_by=reviewer_id,
    )


@patch(
    "app.services.ticket_service."
    "approve_ticket"
)
@patch(
    "app.services.ticket_service."
    "get_ticket_for_review"
)
def test_already_approved_ticket_cannot_be_approved_again(
    mock_get_ticket,
    mock_approve_ticket,
):
    ticket_id = str(uuid4())

    mock_get_ticket.return_value = {
        "id": ticket_id,
        "status": "approved",
        "approval_status": "approved",
    }

    with pytest.raises(
        TicketAlreadyDecidedError,
        match="already been decided",
    ):
        decide_ticket_approval(
            ticket_id=ticket_id,
            reviewer_id=str(uuid4()),
            approved=True,
        )

    mock_approve_ticket.assert_not_called()


@patch(
    "app.services.ticket_service."
    "reject_ticket"
)
@patch(
    "app.services.ticket_service."
    "get_ticket_for_review"
)
def test_rejected_ticket_cannot_be_decided_again(
    mock_get_ticket,
    mock_reject_ticket,
):
    ticket_id = str(uuid4())

    mock_get_ticket.return_value = {
        "id": ticket_id,
        "status": "rejected",
        "approval_status": "rejected",
    }

    with pytest.raises(
        TicketAlreadyDecidedError,
        match="already been decided",
    ):
        decide_ticket_approval(
            ticket_id=ticket_id,
            reviewer_id=str(uuid4()),
            approved=False,
        )

    mock_reject_ticket.assert_not_called()


@patch(
    "app.services.ticket_service."
    "approve_ticket"
)
@patch(
    "app.services.ticket_service."
    "get_ticket_for_review"
)
def test_concurrent_approval_failure_is_detected(
    mock_get_ticket,
    mock_approve_ticket,
):
    """
    Simulate another reviewer deciding the ticket between
    Harbor's initial read and conditional database update.
    """

    ticket_id = str(uuid4())

    mock_get_ticket.return_value = {
        "id": ticket_id,
        "status": "pending_approval",
        "approval_status": "pending",
    }

    # The repository returns no row when its conditional
    # update finds that the ticket is no longer pending.
    mock_approve_ticket.return_value = None

    with pytest.raises(
        TicketAlreadyDecidedError,
        match="already been decided",
    ):
        decide_ticket_approval(
            ticket_id=ticket_id,
            reviewer_id=str(uuid4()),
            approved=True,
        )


@patch(
    "app.services.ticket_service."
    "approve_ticket"
)
@patch(
    "app.services.ticket_service."
    "reject_ticket"
)
@patch(
    "app.services.ticket_service."
    "get_ticket_for_review"
)
def test_approval_changes_only_internal_ticket_state(
    mock_get_ticket,
    mock_reject_ticket,
    mock_approve_ticket,
):
    """
    Step 10.5 performs only Harbor's internal approval
    transition.

    External integrations will be connected in a later step.
    """

    ticket_id = str(uuid4())
    reviewer_id = str(uuid4())

    mock_get_ticket.return_value = {
        "id": ticket_id,
        "status": "pending_approval",
        "approval_status": "pending",
    }

    mock_approve_ticket.return_value = {
        "id": ticket_id,
        "status": "approved",
        "approval_status": "approved",
        "approved_by": reviewer_id,
        "approved_at": None,
    }

    result = decide_ticket_approval(
        ticket_id=ticket_id,
        reviewer_id=reviewer_id,
        approved=True,
    )

    assert result.status == "approved"

    mock_approve_ticket.assert_called_once_with(
        ticket_id=ticket_id,
        approved_by=reviewer_id,
    )

    mock_reject_ticket.assert_not_called()