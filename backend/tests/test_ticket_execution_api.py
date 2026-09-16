from uuid import uuid4

import pytest
from fastapi import HTTPException

import app.api.tickets as tickets_api
from app.services.ticket_execution_service import (
    TicketAlreadyExecutedError,
    TicketExecutionClaimError,
    TicketExecutionNotFoundError,
    TicketExecutionPersistenceError,
    TicketExternalExecutionError,
    TicketNotApprovedForExecutionError,
)


TICKET_ID = uuid4()


def fake_support_agent() -> dict:
    """
    Represent an already-authenticated support agent.

    RBAC itself is tested separately. These tests focus only
    on the execution endpoint's service call and HTTP mapping.
    """

    return {
        "id": str(uuid4()),
        "email": "agent@example.com",
        "role": "support_agent",
    }


def build_executed_ticket() -> dict:
    """
    Minimal executed ticket returned by the mocked service.

    Because the endpoint function is called directly, FastAPI
    response-model serialization is intentionally outside the
    scope of this focused test.
    """

    return {
        "id": str(TICKET_ID),
        "status": "open",
        "approval_status": "approved",
        "monday_item_id": "2859744731",
    }


def test_execute_ticket_success(
    monkeypatch,
):
    """
    The API function should forward the ticket ID to the
    execution service and return its successful result.
    """

    expected = build_executed_ticket()

    def fake_execute(
        *,
        ticket_id,
    ):
        assert ticket_id == str(
            TICKET_ID
        )

        return expected

    monkeypatch.setattr(
        tickets_api,
        "execute_approved_ticket",
        fake_execute,
    )

    result = tickets_api.execute_ticket(
        ticket_id=TICKET_ID,
        current_user=fake_support_agent(),
    )

    assert result == expected
    assert result["status"] == "open"

    assert (
        result["monday_item_id"]
        == "2859744731"
    )


@pytest.mark.parametrize(
    (
        "service_exception",
        "expected_status",
    ),
    [
        (
            TicketExecutionNotFoundError(
                "Support ticket was not found."
            ),
            404,
        ),
        (
            TicketNotApprovedForExecutionError(
                "Support ticket has not been "
                "approved for external execution."
            ),
            409,
        ),
        (
            TicketAlreadyExecutedError(
                "Support ticket has already been "
                "executed externally."
            ),
            409,
        ),
        (
            TicketExecutionClaimError(
                "Support ticket is currently being "
                "executed by another worker."
            ),
            409,
        ),
        (
            TicketExternalExecutionError(
                "Monday synchronization failed."
            ),
            502,
        ),
        (
            TicketExecutionPersistenceError(
                "Harbor could not persist the "
                "execution result."
            ),
            500,
        ),
    ],
)
def test_execution_error_mapping(
    monkeypatch,
    service_exception,
    expected_status,
):
    """
    Domain-level execution failures should become predictable
    HTTP errors for Harbor's API clients.
    """

    def fake_execute(
        *,
        ticket_id,
    ):
        assert ticket_id == str(
            TICKET_ID
        )

        raise service_exception

    monkeypatch.setattr(
        tickets_api,
        "execute_approved_ticket",
        fake_execute,
    )

    with pytest.raises(
        HTTPException
    ) as exc_info:
        tickets_api.execute_ticket(
            ticket_id=TICKET_ID,
            current_user=fake_support_agent(),
        )

    assert (
        exc_info.value.status_code
        == expected_status
    )

    assert (
        exc_info.value.detail
        == str(service_exception)
    )


def test_execution_endpoint_passes_uuid_as_string(
    monkeypatch,
):
    """
    The API boundary receives a UUID while the execution
    service uses its string representation.
    """

    captured_ticket_id = None

    def fake_execute(
        *,
        ticket_id,
    ):
        nonlocal captured_ticket_id

        captured_ticket_id = ticket_id

        return build_executed_ticket()

    monkeypatch.setattr(
        tickets_api,
        "execute_approved_ticket",
        fake_execute,
    )

    tickets_api.execute_ticket(
        ticket_id=TICKET_ID,
        current_user=fake_support_agent(),
    )

    assert captured_ticket_id == str(
        TICKET_ID
    )

    assert isinstance(
        captured_ticket_id,
        str,
    )