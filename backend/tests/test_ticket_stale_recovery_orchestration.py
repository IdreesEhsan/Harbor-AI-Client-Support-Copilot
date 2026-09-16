from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.services.ticket_execution_service import (
    TicketExecutionClaimError,
    TicketExecutionPersistenceError,
    execute_approved_ticket,
)


TICKET_ID = "ticket-123"

OLD_CLAIM_ID = (
    "550e8400-e29b-41d4-a716-446655440000"
)

NEW_CLAIM_ID = (
    "123e4567-e89b-12d3-a456-426614174000"
)

IDEMPOTENCY_KEY = "harbor-test-key"

MONDAY_ITEM_ID = "2859744731"


def build_stale_ticket() -> dict:
    """
    Build an executing ticket whose lease is old enough to
    be eligible for controlled recovery.
    """

    return {
        "id": TICKET_ID,
        "user_id": "user-123",
        "conversation_id": "conversation-123",
        "title": "Customer needs human support",
        "description": (
            "Customer requested escalation to a "
            "support agent."
        ),
        "severity": "high",
        "approval_status": "approved",
        "status": "executing",
        "idempotency_key": IDEMPOTENCY_KEY,
        "execution_claim_id": OLD_CLAIM_ID,
        "execution_started_at": (
            datetime.now(timezone.utc)
            - timedelta(minutes=10)
        ).isoformat(),
        "monday_item_id": None,
    }


def build_recovered_ticket() -> dict:
    """
    Represent the trusted database row returned after Harbor
    atomically replaces the stale execution claim.
    """

    ticket = build_stale_ticket()

    ticket["execution_claim_id"] = (
        NEW_CLAIM_ID
    )

    ticket["execution_started_at"] = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    return ticket


def build_open_ticket() -> dict:
    """
    Represent the final Harbor ticket after successful
    Monday synchronization.
    """

    ticket = build_recovered_ticket()

    ticket.update(
        {
            "status": "open",
            "monday_item_id": (
                MONDAY_ITEM_ID
            ),
            "external_status": "Open",
            "execution_claim_id": None,
            "execution_started_at": None,
        }
    )

    return ticket


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
    "recover_stale_execution_claim"
)
@patch(
    "app.services.ticket_execution_service."
    "is_execution_lease_stale"
)
@patch(
    "app.services.ticket_execution_service."
    "authorize_approved_tool_execution"
)
@patch(
    "app.services.ticket_execution_service."
    "get_ticket_for_review"
)
def test_stale_ticket_reuses_existing_monday_item(
    mock_get_ticket,
    mock_authorize_tool,
    mock_is_stale,
    mock_recover,
    mock_find_monday,
    mock_create_monday,
    mock_mark_executed,
):
    """
    If a previous worker created the Monday item but crashed
    before Harbor persisted it, recovery must reuse that item
    instead of creating a duplicate.
    """

    stale_ticket = build_stale_ticket()
    recovered_ticket = (
        build_recovered_ticket()
    )
    open_ticket = build_open_ticket()

    mock_get_ticket.return_value = (
        stale_ticket
    )

    mock_is_stale.return_value = True

    mock_recover.return_value = (
        recovered_ticket
    )

    mock_find_monday.return_value = {
        "id": MONDAY_ITEM_ID,
        "name": (
            "Customer needs human support"
        ),
    }

    mock_mark_executed.return_value = (
        open_ticket
    )

    result = execute_approved_ticket(
        ticket_id=TICKET_ID
    )

    assert result == open_ticket

    mock_authorize_tool.assert_called_once_with(
        "create_escalation",
        approval_status="approved",
    )

    mock_is_stale.assert_called_once_with(
        execution_started_at=(
            stale_ticket[
                "execution_started_at"
            ]
        )
    )

    mock_recover.assert_called_once_with(
        ticket_id=TICKET_ID,
        previous_claim_id=(
            OLD_CLAIM_ID
        ),
    )

    mock_find_monday.assert_called_once_with(
        idempotency_key=(
            IDEMPOTENCY_KEY
        )
    )

    # Critical idempotency assertion:
    # an existing Monday item means no create mutation.
    mock_create_monday.assert_not_called()

    # Critical ownership assertion:
    # finalization uses the NEW recovery claim.
    mock_mark_executed.assert_called_once_with(
        ticket_id=TICKET_ID,
        monday_item_id=MONDAY_ITEM_ID,
        execution_claim_id=(
            NEW_CLAIM_ID
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
    "recover_stale_execution_claim"
)
@patch(
    "app.services.ticket_execution_service."
    "is_execution_lease_stale"
)
@patch(
    "app.services.ticket_execution_service."
    "authorize_approved_tool_execution"
)
@patch(
    "app.services.ticket_execution_service."
    "get_ticket_for_review"
)
def test_stale_ticket_creates_when_monday_item_missing(
    mock_get_ticket,
    mock_authorize_tool,
    mock_is_stale,
    mock_recover,
    mock_find_monday,
    mock_create_monday,
    mock_mark_executed,
):
    """
    If the stale worker never created the external item, the
    new lease owner may create exactly one Monday item.
    """

    stale_ticket = build_stale_ticket()
    recovered_ticket = (
        build_recovered_ticket()
    )
    open_ticket = build_open_ticket()

    mock_get_ticket.return_value = (
        stale_ticket
    )

    mock_is_stale.return_value = True

    mock_recover.return_value = (
        recovered_ticket
    )

    mock_find_monday.return_value = None

    mock_create_monday.return_value = {
        "id": MONDAY_ITEM_ID,
        "name": (
            "Customer needs human support"
        ),
    }

    mock_mark_executed.return_value = (
        open_ticket
    )

    result = execute_approved_ticket(
        ticket_id=TICKET_ID
    )

    assert result == open_ticket

    mock_find_monday.assert_called_once_with(
        idempotency_key=(
            IDEMPOTENCY_KEY
        )
    )

    mock_create_monday.assert_called_once_with(
        title=(
            recovered_ticket["title"]
        ),
        description=(
            recovered_ticket[
                "description"
            ]
        ),
        severity=(
            recovered_ticket["severity"]
        ),
        harbor_ticket_id=TICKET_ID,
        idempotency_key=(
            IDEMPOTENCY_KEY
        ),
    )

    mock_mark_executed.assert_called_once_with(
        ticket_id=TICKET_ID,
        monday_item_id=MONDAY_ITEM_ID,
        execution_claim_id=(
            NEW_CLAIM_ID
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
    "recover_stale_execution_claim"
)
@patch(
    "app.services.ticket_execution_service."
    "is_execution_lease_stale"
)
@patch(
    "app.services.ticket_execution_service."
    "authorize_approved_tool_execution"
)
@patch(
    "app.services.ticket_execution_service."
    "get_ticket_for_review"
)
def test_active_lease_never_reaches_monday(
    mock_get_ticket,
    mock_authorize_tool,
    mock_is_stale,
    mock_recover,
    mock_find_monday,
    mock_create_monday,
    mock_mark_executed,
):
    """
    An active execution lease must stop before Harbor reads
    from or writes to Monday.com.
    """

    ticket = build_stale_ticket()

    ticket["execution_started_at"] = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    mock_get_ticket.return_value = ticket
    mock_is_stale.return_value = False

    with pytest.raises(
        TicketExecutionClaimError,
        match="currently being executed",
    ):
        execute_approved_ticket(
            ticket_id=TICKET_ID
        )

    mock_recover.assert_not_called()
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
    "recover_stale_execution_claim"
)
@patch(
    "app.services.ticket_execution_service."
    "is_execution_lease_stale"
)
@patch(
    "app.services.ticket_execution_service."
    "authorize_approved_tool_execution"
)
@patch(
    "app.services.ticket_execution_service."
    "get_ticket_for_review"
)
def test_lost_recovery_race_never_reaches_monday(
    mock_get_ticket,
    mock_authorize_tool,
    mock_is_stale,
    mock_recover,
    mock_find_monday,
    mock_create_monday,
    mock_mark_executed,
):
    """
    If another worker wins stale takeover, the losing worker
    must stop before any Monday.com operation.
    """

    mock_get_ticket.return_value = (
        build_stale_ticket()
    )

    mock_is_stale.return_value = True

    # CAS failed because another worker replaced the old
    # claim first.
    mock_recover.return_value = None

    with pytest.raises(
        TicketExecutionClaimError,
        match="could not be recovered",
    ):
        execute_approved_ticket(
            ticket_id=TICKET_ID
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
    "recover_stale_execution_claim"
)
@patch(
    "app.services.ticket_execution_service."
    "is_execution_lease_stale"
)
@patch(
    "app.services.ticket_execution_service."
    "authorize_approved_tool_execution"
)
@patch(
    "app.services.ticket_execution_service."
    "get_ticket_for_review"
)
def test_recovery_finalization_failure_is_reported(
    mock_get_ticket,
    mock_authorize_tool,
    mock_is_stale,
    mock_recover,
    mock_find_monday,
    mock_create_monday,
    mock_mark_executed,
):
    """
    If Monday already contains the item but Harbor cannot
    finalize its DB state, the service must report partial
    persistence rather than attempting another create.
    """

    mock_get_ticket.return_value = (
        build_stale_ticket()
    )

    mock_is_stale.return_value = True

    mock_recover.return_value = (
        build_recovered_ticket()
    )

    mock_find_monday.return_value = {
        "id": MONDAY_ITEM_ID,
        "name": (
            "Customer needs human support"
        ),
    }

    mock_mark_executed.return_value = None

    with pytest.raises(
        TicketExecutionPersistenceError,
        match="could not persist",
    ):
        execute_approved_ticket(
            ticket_id=TICKET_ID
        )

    # Existing external item must still prevent a second
    # create mutation.
    mock_create_monday.assert_not_called()

    mock_mark_executed.assert_called_once_with(
        ticket_id=TICKET_ID,
        monday_item_id=MONDAY_ITEM_ID,
        execution_claim_id=(
            NEW_CLAIM_ID
        ),
    )