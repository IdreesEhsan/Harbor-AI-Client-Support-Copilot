import logging
from typing import Any

from app.agent.tools import (
    authorize_approved_tool_execution,
)

from app.integrations.monday import (
    MondayAPIError,
    create_support_ticket_item,
    find_support_ticket_by_idempotency_key,
)

from app.integrations.n8n import (
    N8NConfigurationError,
    N8NWebhookError,
    send_ticket_execution_event,
)

from app.repositories.ticket_repository import (
    claim_ticket_for_execution,
    get_ticket_for_review,
    mark_ticket_executed,
    recover_stale_execution_claim,
)

from app.tickets.execution_lease import (
    InvalidExecutionLeaseError,
    is_execution_lease_stale,
)


logger = logging.getLogger(__name__)


class TicketExecutionNotFoundError(Exception):
    """
    Raised when Harbor cannot find the internal support
    ticket requested for execution.
    """


class TicketNotApprovedForExecutionError(
    Exception
):
    """
    Raised when a support ticket has not received persisted
    human approval.
    """


class TicketAlreadyExecutedError(Exception):
    """
    Raised when Harbor already contains evidence that the
    external Monday.com escalation was synchronized.
    """


class TicketExecutionClaimError(Exception):
    """
    Raised when Harbor cannot obtain execution ownership.

    This includes:

    - losing the initial approved -> executing claim;
    - attempting to take over an active lease;
    - losing a stale-lease recovery race;
    - invalid persisted claim metadata.
    """


class TicketExternalExecutionError(
    Exception
):
    """
    Raised when Harbor owns execution but cannot safely
    communicate with Monday.com.
    """


class TicketExecutionPersistenceError(
    Exception
):
    """
    Raised when Monday.com contains the external item but
    Harbor cannot persist the synchronized result.
    """


def get_ticket_for_execution(
    *,
    ticket_id: str,
) -> dict[str, Any]:
    """
    Load a ticket that may participate in execution.

    Human approval must remain persisted as approved.

    Valid workflow states:

        approved
            Normal first execution.

        executing
            Possible stale-lease recovery.
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

    if (
        ticket.get(
            "approval_status"
        )
        != "approved"
    ):
        raise (
            TicketNotApprovedForExecutionError(
                "Support ticket has not been "
                "approved for external execution."
            )
        )

    if ticket.get(
        "monday_item_id"
    ):
        raise TicketAlreadyExecutedError(
            "Support ticket has already been "
            "executed externally."
        )

    ticket_status = ticket.get(
        "status"
    )

    if ticket_status not in {
        "approved",
        "executing",
    }:
        raise (
            TicketNotApprovedForExecutionError(
                "Support ticket is not in an "
                "executable workflow state."
            )
        )

    return ticket


def authorize_ticket_execution(
    *,
    ticket_id: str,
) -> dict[str, Any]:
    """
    Establish Harbor's trusted authorization boundary.

    Persisted human approval is checked before Harbor's
    centralized write-tool authorization policy.
    """

    ticket = (
        get_ticket_for_execution(
            ticket_id=ticket_id
        )
    )

    authorize_approved_tool_execution(
        "create_escalation",
        approval_status=(
            ticket[
                "approval_status"
            ]
        ),
    )

    return ticket


def claim_authorized_ticket(
    *,
    ticket: dict[str, Any],
) -> dict[str, Any]:
    """
    Obtain execution ownership for an authorized ticket.

    New ticket:

        approved
            ↓
        atomic claim
            ↓
        executing

    Recovery:

        executing
            ↓
        check lease
            ↓
        stale?
            ↓
        compare-and-swap claim recovery
    """

    ticket_id = ticket.get(
        "id"
    )

    if ticket_id is None:
        raise TicketExecutionClaimError(
            "Authorized support ticket does not "
            "contain a valid ticket ID."
        )

    ticket_id = str(
        ticket_id
    )

    ticket_status = ticket.get(
        "status"
    )

    # --------------------------------------------------------
    # Normal first execution
    # --------------------------------------------------------

    if ticket_status == "approved":
        claimed_ticket = (
            claim_ticket_for_execution(
                ticket_id
            )
        )

        if claimed_ticket is None:
            raise TicketExecutionClaimError(
                "Support ticket could not be "
                "claimed for external execution."
            )

        return claimed_ticket

    # --------------------------------------------------------
    # Stale execution recovery
    # --------------------------------------------------------

    if ticket_status == "executing":
        previous_claim_id = (
            ticket.get(
                "execution_claim_id"
            )
        )

        execution_started_at = (
            ticket.get(
                "execution_started_at"
            )
        )

        if (
            not isinstance(
                previous_claim_id,
                str,
            )
            or not previous_claim_id.strip()
        ):
            raise TicketExecutionClaimError(
                "Executing support ticket does "
                "not contain a valid execution "
                "claim ID."
            )

        if (
            not isinstance(
                execution_started_at,
                str,
            )
            or not execution_started_at.strip()
        ):
            raise TicketExecutionClaimError(
                "Executing support ticket does "
                "not contain a valid execution "
                "start timestamp."
            )

        previous_claim_id = (
            previous_claim_id.strip()
        )

        execution_started_at = (
            execution_started_at.strip()
        )

        try:
            stale = (
                is_execution_lease_stale(
                    execution_started_at=(
                        execution_started_at
                    )
                )
            )

        except (
            InvalidExecutionLeaseError,
            TypeError,
        ) as exc:
            raise TicketExecutionClaimError(
                "Executing support ticket "
                "contains invalid execution "
                "lease metadata."
            ) from exc

        if not stale:
            raise TicketExecutionClaimError(
                "Support ticket is currently "
                "being executed by another worker."
            )

        recovered_ticket = (
            recover_stale_execution_claim(
                ticket_id=ticket_id,
                previous_claim_id=(
                    previous_claim_id
                ),
            )
        )

        if recovered_ticket is None:
            raise TicketExecutionClaimError(
                "Stale support ticket execution "
                "claim could not be recovered."
            )

        return recovered_ticket

    raise TicketExecutionClaimError(
        "Support ticket is not in a "
        "claimable execution state."
    )


def get_execution_claim_id(
    *,
    ticket: dict[str, Any],
) -> str:
    """
    Extract execution ownership from Harbor's trusted
    persisted ticket record.
    """

    execution_claim_id = (
        ticket.get(
            "execution_claim_id"
        )
    )

    if (
        not isinstance(
            execution_claim_id,
            str,
        )
        or not execution_claim_id.strip()
    ):
        raise TicketExecutionClaimError(
            "Claimed support ticket does not "
            "contain a valid execution claim ID."
        )

    return (
        execution_claim_id.strip()
    )


def execute_approved_ticket(
    *,
    ticket_id: str,
) -> dict[str, Any]:
    """
    Safely execute one approved Harbor escalation.

    Final architecture:

        Human Approval
              ↓
        Atomic Claim
              ↓
        Monday Lookup
              ↓
        Reuse / Create
              ↓
        Harbor Finalization
              ↓
        n8n Cloud
          ┌───┼────┐
          ↓   ↓    ↓
        Gmail Audit Snowflake

    n8n is intentionally invoked only AFTER Harbor safely
    finalizes the Monday synchronization.
    """

    # --------------------------------------------------------
    # 1. Verify persisted approval and tool authorization
    # --------------------------------------------------------

    authorized_ticket = (
        authorize_ticket_execution(
            ticket_id=ticket_id
        )
    )

    # --------------------------------------------------------
    # 2. Obtain exclusive execution ownership
    # --------------------------------------------------------

    ticket = (
        claim_authorized_ticket(
            ticket=authorized_ticket
        )
    )

    execution_claim_id = (
        get_execution_claim_id(
            ticket=ticket
        )
    )

    # --------------------------------------------------------
    # 3. Validate deterministic idempotency key
    # --------------------------------------------------------

    idempotency_key = (
        ticket.get(
            "idempotency_key"
        )
    )

    if (
        not isinstance(
            idempotency_key,
            str,
        )
        or not idempotency_key.strip()
    ):
        raise TicketExternalExecutionError(
            "Support ticket does not contain "
            "a valid idempotency key."
        )

    idempotency_key = (
        idempotency_key.strip()
    )

    # --------------------------------------------------------
    # 4. Monday.com lookup/create
    # --------------------------------------------------------

    try:
        monday_item = (
            find_support_ticket_by_idempotency_key(
                idempotency_key=(
                    idempotency_key
                )
            )
        )

        if monday_item is None:
            monday_item = (
                create_support_ticket_item(
                    title=(
                        ticket["title"]
                    ),
                    description=(
                        ticket[
                            "description"
                        ]
                    ),
                    severity=(
                        ticket[
                            "severity"
                        ]
                    ),
                    harbor_ticket_id=str(
                        ticket["id"]
                    ),
                    idempotency_key=(
                        idempotency_key
                    ),
                )
            )

    except MondayAPIError as exc:
        # Keep Harbor in executing state because the result
        # of the external request may be uncertain.
        raise TicketExternalExecutionError(
            "The approved support ticket "
            "could not be safely synchronized "
            "with Monday.com."
        ) from exc

    # --------------------------------------------------------
    # 5. Validate Monday result
    # --------------------------------------------------------

    monday_item_id = (
        monday_item.get(
            "id"
        )
    )

    if not monday_item_id:
        raise TicketExternalExecutionError(
            "Monday.com did not return "
            "a valid item ID."
        )

    # --------------------------------------------------------
    # 6. Finalize Harbor ticket
    # --------------------------------------------------------

    executed_ticket = (
        mark_ticket_executed(
            ticket_id=str(
                ticket["id"]
            ),
            monday_item_id=str(
                monday_item_id
            ),
            execution_claim_id=(
                execution_claim_id
            ),
        )
    )

    if executed_ticket is None:
        raise TicketExecutionPersistenceError(
            "Monday.com contains the support "
            "item, but Harbor could not persist "
            "the execution result."
        )

    # --------------------------------------------------------
    # 7. Dispatch downstream automation event to n8n Cloud
    # --------------------------------------------------------
    #
    # Important:
    #
    # Monday + Harbor execution is already successful.
    #
    # If Gmail, Supabase audit, Snowflake, or n8n itself is
    # temporarily unavailable, Harbor must NOT recreate the
    # Monday item.
    #
    # Therefore downstream automation failure is logged but
    # does not invalidate the completed ticket execution.
    try:
        send_ticket_execution_event(
            executed_ticket
        )

    except N8NConfigurationError:
        logger.exception(
            (
                "Ticket execution completed but n8n "
                "Cloud is not configured. ticket_id=%s"
            ),
            executed_ticket.get(
                "id"
            ),
        )

    except N8NWebhookError:
        logger.exception(
            (
                "Ticket execution completed but n8n "
                "Cloud delivery failed. ticket_id=%s"
            ),
            executed_ticket.get(
                "id"
            ),
        )

    # --------------------------------------------------------
    # 8. Return completed Harbor ticket
    # --------------------------------------------------------

    return executed_ticket