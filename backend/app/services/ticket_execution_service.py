from typing import Any

from app.agent.tools import (
    authorize_approved_tool_execution,
)
from app.integrations.monday import (
    MondayAPIError,
    create_support_ticket_item,
    find_support_ticket_by_idempotency_key,
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


class TicketExecutionNotFoundError(Exception):
    """
    Raised when Harbor cannot find the internal support
    ticket requested for execution.
    """


class TicketNotApprovedForExecutionError(Exception):
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


class TicketExternalExecutionError(Exception):
    """
    Raised when Harbor owns execution but cannot safely
    communicate with Monday.com.
    """


class TicketExecutionPersistenceError(Exception):
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

    Two workflow states are accepted here:

        approved
            Normal first execution.

        executing
            Possible stale-lease recovery.

    Accepting ``executing`` here does NOT grant execution
    ownership. An executing ticket must still pass lease
    validation and atomic stale-claim takeover before any
    Monday.com operation occurs.
    """

    if not isinstance(ticket_id, str):
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

    if ticket.get("approval_status") != "approved":
        raise TicketNotApprovedForExecutionError(
            "Support ticket has not been approved "
            "for external execution."
        )

    if ticket.get("monday_item_id"):
        raise TicketAlreadyExecutedError(
            "Support ticket has already been "
            "executed externally."
        )

    ticket_status = ticket.get("status")

    if ticket_status not in {
        "approved",
        "executing",
    }:
        raise TicketNotApprovedForExecutionError(
            "Support ticket is not in an executable "
            "workflow state."
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

    This function performs no external side effect and does
    not itself grant execution ownership.
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


def claim_authorized_ticket(
    *,
    ticket: dict[str, Any],
) -> dict[str, Any]:
    """
    Obtain execution ownership for an authorized ticket.

    For a new approved ticket:

        approved
            ↓ atomic claim
        executing + new claim ID

    For an already executing ticket:

        inspect lease
            ↓
        active → reject
        stale  → atomic compare-and-swap takeover

    No Monday.com operation is allowed until this function
    returns a trusted claimed ticket.
    """

    ticket_id = ticket.get("id")

    if ticket_id is None:
        raise TicketExecutionClaimError(
            "Authorized support ticket does not contain "
            "a valid ticket ID."
        )

    ticket_id = str(ticket_id)

    ticket_status = ticket.get(
        "status"
    )

    # Normal first execution.
    if ticket_status == "approved":
        claimed_ticket = (
            claim_ticket_for_execution(
                ticket_id
            )
        )

        if claimed_ticket is None:
            raise TicketExecutionClaimError(
                "Support ticket could not be claimed for "
                "external execution."
            )

        return claimed_ticket

    # Recovery path.
    if ticket_status == "executing":
        previous_claim_id = ticket.get(
            "execution_claim_id"
        )

        execution_started_at = ticket.get(
            "execution_started_at"
        )

        if (
            not isinstance(
                previous_claim_id,
                str,
            )
            or not previous_claim_id.strip()
        ):
            raise TicketExecutionClaimError(
                "Executing support ticket does not contain "
                "a valid execution claim ID."
            )

        if (
            not isinstance(
                execution_started_at,
                str,
            )
            or not execution_started_at.strip()
        ):
            raise TicketExecutionClaimError(
                "Executing support ticket does not contain "
                "a valid execution start timestamp."
            )

        previous_claim_id = (
            previous_claim_id.strip()
        )

        execution_started_at = (
            execution_started_at.strip()
        )

        try:
            stale = is_execution_lease_stale(
                execution_started_at=(
                    execution_started_at
                )
            )
        except (
            InvalidExecutionLeaseError,
            TypeError,
        ) as exc:
            raise TicketExecutionClaimError(
                "Executing support ticket contains "
                "invalid execution lease metadata."
            ) from exc

        if not stale:
            raise TicketExecutionClaimError(
                "Support ticket is currently being "
                "executed by another worker."
            )

        # The lease is stale according to Harbor's policy.
        #
        # We still do not own execution until the database
        # compare-and-swap succeeds using the exact previous
        # claim ID that we inspected.
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
                "Stale support ticket execution claim "
                "could not be recovered."
            )

        return recovered_ticket

    # Defensive fallback. get_ticket_for_execution() should
    # already prevent this state from reaching here.
    raise TicketExecutionClaimError(
        "Support ticket is not in a claimable "
        "execution state."
    )


def get_execution_claim_id(
    *,
    ticket: dict[str, Any],
) -> str:
    """
    Extract execution ownership from the trusted database
    record returned by either normal claim or stale takeover.

    This value never comes from user input.
    """

    execution_claim_id = ticket.get(
        "execution_claim_id"
    )

    if (
        not isinstance(
            execution_claim_id,
            str,
        )
        or not execution_claim_id.strip()
    ):
        raise TicketExecutionClaimError(
            "Claimed support ticket does not contain "
            "a valid execution claim ID."
        )

    return execution_claim_id.strip()


def execute_approved_ticket(
    *,
    ticket_id: str,
) -> dict[str, Any]:
    """
    Safely execute or recover one approved Harbor escalation.

    Normal path:

        approved
            ↓
        atomic claim
            ↓
        executing
            ↓
        Monday lookup/create
            ↓
        claim-owned finalization
            ↓
        open

    Recovery path:

        executing
            ↓
        stale lease check
            ↓
        atomic claim takeover
            ↓
        NEW execution claim
            ↓
        Monday idempotency lookup
            ↓
        existing item OR safe create
            ↓
        claim-owned finalization
            ↓
        open

    An active execution lease is never stolen.

    A stale ticket is never blindly reset to ``approved``.

    Monday is always searched by Harbor's idempotency key
    before a new external item is created.
    """

    authorized_ticket = (
        authorize_ticket_execution(
            ticket_id=ticket_id
        )
    )

    # This returns only after the worker has obtained trusted
    # execution ownership through either:
    #
    # approved -> executing
    #
    # or:
    #
    # stale executing claim -> new executing claim
    ticket = claim_authorized_ticket(
        ticket=authorized_ticket
    )

    execution_claim_id = (
        get_execution_claim_id(
            ticket=ticket
        )
    )

    idempotency_key = ticket.get(
        "idempotency_key"
    )

    if (
        not isinstance(
            idempotency_key,
            str,
        )
        or not idempotency_key.strip()
    ):
        raise TicketExternalExecutionError(
            "Support ticket does not contain a valid "
            "idempotency key."
        )

    idempotency_key = (
        idempotency_key.strip()
    )

    try:
        # This lookup is essential for stale recovery.
        #
        # The previous worker may have successfully created
        # the Monday item and crashed before Harbor persisted
        # monday_item_id.
        monday_item = (
            find_support_ticket_by_idempotency_key(
                idempotency_key=(
                    idempotency_key
                )
            )
        )

        if monday_item is None:
            # No external item was found after this worker
            # obtained execution ownership, so creation may
            # proceed.
            monday_item = (
                create_support_ticket_item(
                    title=ticket["title"],
                    description=(
                        ticket["description"]
                    ),
                    severity=(
                        ticket["severity"]
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
        # Keep the ticket executing.
        #
        # We cannot safely infer whether Monday accepted an
        # external mutation when communication fails.
        raise TicketExternalExecutionError(
            "The approved support ticket could not be "
            "safely synchronized with Monday.com."
        ) from exc

    monday_item_id = monday_item.get(
        "id"
    )

    if not monday_item_id:
        raise TicketExternalExecutionError(
            "Monday.com did not return a valid item ID."
        )

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
        # Either persistence failed or execution ownership
        # changed before finalization.
        #
        # Monday may already contain the item, so never
        # blindly issue another external create here.
        raise TicketExecutionPersistenceError(
            "Monday.com contains the support item, but "
            "Harbor could not persist the execution result."
        )

    return executed_ticket