from unittest.mock import patch

import pytest

from app.agent.tools import (
    ToolExecutionBlockedError,
)
from app.services.ticket_execution_service import (
    TicketAlreadyExecutedError,
    TicketExecutionNotFoundError,
    TicketNotApprovedForExecutionError,
    authorize_ticket_execution,
    get_ticket_for_execution,
)


def build_ticket(
    *,
    approval_status="approved",
    status="approved",
    monday_item_id=None,
):
    """
    Build a minimal persisted ticket representation for
    execution-service tests.
    """

    return {
        "id": (
            "11111111-1111-1111-1111-111111111111"
        ),
        "user_id": (
            "22222222-2222-2222-2222-222222222222"
        ),
        "conversation_id": (
            "33333333-3333-3333-3333-333333333333"
        ),
        "approval_status": approval_status,
        "status": status,
        "monday_item_id": monday_item_id,
    }


@patch(
    "app.services.ticket_execution_service."
    "get_ticket_for_review"
)
def test_get_ticket_for_execution_returns_approved_ticket(
    mock_get_ticket,
):
    """
    A correctly approved, not-yet-executed ticket is eligible
    to cross the execution boundary.
    """

    ticket = build_ticket()

    mock_get_ticket.return_value = ticket

    result = get_ticket_for_execution(
        ticket_id=ticket["id"]
    )

    assert result == ticket

    mock_get_ticket.assert_called_once_with(
        ticket["id"]
    )


@patch(
    "app.services.ticket_execution_service."
    "get_ticket_for_review"
)
def test_missing_ticket_cannot_execute(
    mock_get_ticket,
):
    """
    External execution cannot occur for a ticket that does
    not exist in Harbor's trusted persistence layer.
    """

    mock_get_ticket.return_value = None

    with pytest.raises(
        TicketExecutionNotFoundError,
        match="not found",
    ):
        get_ticket_for_execution(
            ticket_id=(
                "11111111-1111-1111-1111-111111111111"
            )
        )


@patch(
    "app.services.ticket_execution_service."
    "get_ticket_for_review"
)
def test_pending_ticket_cannot_execute(
    mock_get_ticket,
):
    """
    Pending human approval must prevent execution.
    """

    mock_get_ticket.return_value = (
        build_ticket(
            approval_status="pending",
            status="pending_approval",
        )
    )

    with pytest.raises(
        TicketNotApprovedForExecutionError,
        match="not been approved",
    ):
        get_ticket_for_execution(
            ticket_id=(
                "11111111-1111-1111-1111-111111111111"
            )
        )


@patch(
    "app.services.ticket_execution_service."
    "get_ticket_for_review"
)
def test_rejected_ticket_cannot_execute(
    mock_get_ticket,
):
    """
    A human-rejected ticket must never reach an external
    side effect.
    """

    mock_get_ticket.return_value = (
        build_ticket(
            approval_status="rejected",
            status="rejected",
        )
    )

    with pytest.raises(
        TicketNotApprovedForExecutionError,
        match="not been approved",
    ):
        get_ticket_for_execution(
            ticket_id=(
                "11111111-1111-1111-1111-111111111111"
            )
        )


@patch(
    "app.services.ticket_execution_service."
    "get_ticket_for_review"
)
def test_inconsistent_approval_state_cannot_execute(
    mock_get_ticket,
):
    """
    approval_status alone is insufficient.

    Harbor requires both approval fields to represent the
    expected approved lifecycle state.
    """

    mock_get_ticket.return_value = (
        build_ticket(
            approval_status="approved",
            status="rejected",
        )
    )

    with pytest.raises(
        TicketNotApprovedForExecutionError
    ):
        get_ticket_for_execution(
            ticket_id=(
                "11111111-1111-1111-1111-111111111111"
            )
        )


@patch(
    "app.services.ticket_execution_service."
    "get_ticket_for_review"
)
def test_already_executed_ticket_is_blocked(
    mock_get_ticket,
):
    """
    An existing Monday.com item ID is external execution
    evidence and prevents a duplicate side effect.
    """

    mock_get_ticket.return_value = (
        build_ticket(
            monday_item_id="123456789"
        )
    )

    with pytest.raises(
        TicketAlreadyExecutedError,
        match="already been executed",
    ):
        get_ticket_for_execution(
            ticket_id=(
                "11111111-1111-1111-1111-111111111111"
            )
        )


def test_ticket_id_must_be_string():
    """
    Invalid execution identifiers should fail before any
    repository access occurs.
    """

    with pytest.raises(
        TypeError,
        match="must be a string",
    ):
        get_ticket_for_execution(
            ticket_id=123,
        )


def test_ticket_id_cannot_be_empty():
    """
    Empty identifiers must not reach the persistence layer.
    """

    with pytest.raises(
        ValueError,
        match="cannot be empty",
    ):
        get_ticket_for_execution(
            ticket_id="   ",
        )


@patch(
    "app.services.ticket_execution_service."
    "authorize_approved_tool_execution"
)
@patch(
    "app.services.ticket_execution_service."
    "get_ticket_for_review"
)
def test_authorize_ticket_execution_uses_persisted_approval(
    mock_get_ticket,
    mock_authorize,
):
    """
    The approval-aware tool boundary receives approval state
    loaded from persistence rather than caller-controlled
    input.
    """

    ticket = build_ticket()

    mock_get_ticket.return_value = ticket

    result = authorize_ticket_execution(
        ticket_id=ticket["id"]
    )

    assert result == ticket

    mock_authorize.assert_called_once_with(
        "create_escalation",
        approval_status="approved",
    )


@patch(
    "app.services.ticket_execution_service."
    "authorize_approved_tool_execution"
)
@patch(
    "app.services.ticket_execution_service."
    "get_ticket_for_review"
)
def test_pending_ticket_never_reaches_tool_authorization(
    mock_get_ticket,
    mock_authorize,
):
    """
    Invalid persisted lifecycle state is rejected before the
    write-tool authorization boundary is reached.
    """

    ticket = build_ticket(
        approval_status="pending",
        status="pending_approval",
    )

    mock_get_ticket.return_value = ticket

    with pytest.raises(
        TicketNotApprovedForExecutionError
    ):
        authorize_ticket_execution(
            ticket_id=ticket["id"]
        )

    mock_authorize.assert_not_called()


@patch(
    "app.services.ticket_execution_service."
    "authorize_approved_tool_execution"
)
@patch(
    "app.services.ticket_execution_service."
    "get_ticket_for_review"
)
def test_tool_policy_can_still_block_execution(
    mock_get_ticket,
    mock_authorize,
):
    """
    Persisted human approval does not bypass Harbor's
    centralized tool security policy.
    """

    ticket = build_ticket()

    mock_get_ticket.return_value = ticket

    mock_authorize.side_effect = (
        ToolExecutionBlockedError(
            "Tool is not authorized."
        )
    )

    with pytest.raises(
        ToolExecutionBlockedError
    ):
        authorize_ticket_execution(
            ticket_id=ticket["id"]
        )


@patch(
    "app.services.ticket_execution_service."
    "authorize_approved_tool_execution"
)
@patch(
    "app.services.ticket_execution_service."
    "get_ticket_for_review"
)
def test_already_executed_ticket_never_reaches_authorization(
    mock_get_ticket,
    mock_authorize,
):
    """
    Duplicate-execution protection runs before the external
    write capability can be authorized again.
    """

    ticket = build_ticket(
        monday_item_id="123456789"
    )

    mock_get_ticket.return_value = ticket

    with pytest.raises(
        TicketAlreadyExecutedError
    ):
        authorize_ticket_execution(
            ticket_id=ticket["id"]
        )

    mock_authorize.assert_not_called()