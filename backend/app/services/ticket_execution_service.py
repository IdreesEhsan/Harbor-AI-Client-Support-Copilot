from typing import Any

from app.agent.tools import (
    authorize_approved_tool_execution,
)
from app.repositories.ticket_repository import (
    get_ticket_for_review,
)


class TicketExecutionNotFoundError(Exception):
    """
    Raised when Harbor cannot find the internal support
    ticket requested for execution.
    """


class TicketNotApprovedForExecutionError(Exception):
    """
    Raised when a support ticket has not reached the exact
    persisted approval state required for a side effect.
    """


class TicketAlreadyExecutedError(Exception):
    """
    Raised when the internal ticket already contains evidence
    that its external escalation has been created.

    This protects later external integrations from duplicate
    execution during retries.
    """


def get_ticket_for_execution(
    *,
    ticket_id: str,
) -> dict[str, Any]:
    """
    Load and validate the persisted ticket before external
    execution is permitted.

    Approval is determined only from Harbor's trusted ticket
    storage. A caller cannot supply an ``approved=True``
    boolean to bypass the persisted HITL decision.

    The ticket must satisfy both:

        approval_status == "approved"
        status == "approved"

    External execution evidence is also checked before the
    caller is allowed to continue.
    """

    if not isinstance(
        ticket_id,
        str,
    ):
        raise TypeError(
            "ticket_id must be a string."
        )

    ticket_id = ticket_id.strip()

    if not ticket_id:
        raise ValueError(
            "ticket_id cannot be empty."
        )

    ticket = get_ticket_for_review(
        ticket_id
    )

    if ticket is None:
        raise TicketExecutionNotFoundError(
            "Support ticket was not found."
        )

    approval_status = ticket.get(
        "approval_status"
    )

    ticket_status = ticket.get(
        "status"
    )

    if (
        approval_status != "approved"
        or ticket_status != "approved"
    ):
        raise TicketNotApprovedForExecutionError(
            "Support ticket has not been approved "
            "for external execution."
        )

    # monday_item_id will later be written only after the
    # external Monday.com item has been successfully created.
    # If it already exists, repeating the side effect could
    # create a duplicate external ticket.
    if ticket.get("monday_item_id"):
        raise TicketAlreadyExecutedError(
            "Support ticket has already been "
            "executed externally."
        )

    return ticket


def authorize_ticket_execution(
    *,
    ticket_id: str,
) -> dict[str, Any]:
    """
    Establish Harbor's trusted execution boundary for an
    approved support ticket.

    This function does not perform the external side effect.
    It only proves that the persisted ticket is currently
    eligible to execute the registered create_escalation
    capability.

    A later integration adapter must call this function
    before contacting Monday.com.
    """

    ticket = get_ticket_for_execution(
        ticket_id=ticket_id
    )

    authorize_approved_tool_execution(
        "create_escalation",
        approval_status=(
            ticket["approval_status"]
        ),
    )

    return ticket