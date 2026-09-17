import logging
from time import perf_counter
from typing import Any

from app.agent.tools import (
    authorize_approved_tool_execution,
)

from app.integrations.monday import (
    MondayAPIError,
    MondayConfigurationError,
    create_support_ticket_item,
    find_support_ticket_by_idempotency_key,
)

from app.integrations.n8n import (
    dispatch_ticket_execution_event,
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


logger = logging.getLogger(
    __name__
)


# ============================================================
# EXCEPTIONS
# ============================================================

class TicketExecutionNotFoundError(Exception):
    """
    Harbor could not find the internal support ticket.
    """


class TicketNotApprovedForExecutionError(
    Exception
):
    """
    Ticket has not received persisted human approval.
    """


class TicketAlreadyExecutedError(Exception):
    """
    Harbor already has proof of Monday.com execution.
    """


class TicketExecutionClaimError(Exception):
    """
    Harbor could not obtain exclusive execution ownership.
    """


class TicketExternalExecutionError(
    Exception
):
    """
    Harbor owns execution but Monday.com could not be used
    safely.
    """


class TicketExecutionPersistenceError(
    Exception
):
    """
    Monday.com succeeded but Harbor could not persist the
    external execution result.
    """


# ============================================================
# TIMING
# ============================================================

def _milliseconds(
    started_at: float,
) -> float:
    return (
        (
            perf_counter()
            - started_at
        )
        * 1000
    )


# ============================================================
# LOAD EXECUTABLE TICKET
# ============================================================

def get_ticket_for_execution(
    *,
    ticket_id: str,
) -> dict[str, Any]:
    """
    Load an internally-approved ticket that may participate
    in execution.

    Valid workflow states:

        approved
        executing
    """

    if not isinstance(
        ticket_id,
        str,
    ):
        raise TypeError(
            "ticket_id must be a string."
        )


    ticket_id = (
        ticket_id.strip()
    )


    if not ticket_id:
        raise ValueError(
            "ticket_id cannot be empty."
        )


    ticket = (
        get_ticket_for_review(
            ticket_id
        )
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
                (
                    "Support ticket has not "
                    "been approved for "
                    "external execution."
                )
            )
        )


    if ticket.get(
        "monday_item_id"
    ):
        raise TicketAlreadyExecutedError(
            (
                "Support ticket has already "
                "been executed externally."
            )
        )


    ticket_status = (
        ticket.get(
            "status"
        )
    )


    if ticket_status not in {
        "approved",
        "executing",
    }:
        raise (
            TicketNotApprovedForExecutionError(
                (
                    "Support ticket is not "
                    "in an executable "
                    "workflow state."
                )
            )
        )


    return ticket


# ============================================================
# AUTHORIZATION BOUNDARY
# ============================================================

def authorize_ticket_execution(
    *,
    ticket_id: str,
) -> dict[str, Any]:
    """
    Verify persisted human approval and then pass through
    Harbor's centralized write-tool authorization policy.
    """

    ticket = (
        get_ticket_for_execution(
            ticket_id=(
                ticket_id
            )
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


# ============================================================
# CLAIM EXECUTION
# ============================================================

def claim_authorized_ticket(
    *,
    ticket: dict[str, Any],
) -> dict[str, Any]:
    """
    Obtain exclusive execution ownership.

    Normal:

        approved
           ↓
        executing

    Recovery:

        executing
           ↓
        stale lease?
           ↓
        recover claim
    """

    ticket_id = (
        ticket.get(
            "id"
        )
    )


    if ticket_id is None:
        raise TicketExecutionClaimError(
            (
                "Authorized support ticket "
                "does not contain a valid "
                "ticket ID."
            )
        )


    ticket_id = str(
        ticket_id
    )


    ticket_status = (
        ticket.get(
            "status"
        )
    )


    # --------------------------------------------------------
    # NORMAL EXECUTION
    # --------------------------------------------------------

    if ticket_status == "approved":

        claimed_ticket = (
            claim_ticket_for_execution(
                ticket_id
            )
        )


        if claimed_ticket is None:
            raise TicketExecutionClaimError(
                (
                    "Support ticket could not "
                    "be claimed for external "
                    "execution."
                )
            )


        return claimed_ticket


    # --------------------------------------------------------
    # STALE CLAIM RECOVERY
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
                (
                    "Executing support ticket "
                    "does not contain a valid "
                    "execution claim ID."
                )
            )


        if (
            not isinstance(
                execution_started_at,
                str,
            )
            or not execution_started_at.strip()
        ):
            raise TicketExecutionClaimError(
                (
                    "Executing support ticket "
                    "does not contain a valid "
                    "execution start timestamp."
                )
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
                (
                    "Executing support ticket "
                    "contains invalid execution "
                    "lease metadata."
                )
            ) from exc


        if not stale:
            raise TicketExecutionClaimError(
                (
                    "Support ticket is currently "
                    "being executed by another worker."
                )
            )


        recovered_ticket = (
            recover_stale_execution_claim(
                ticket_id=(
                    ticket_id
                ),

                previous_claim_id=(
                    previous_claim_id
                ),
            )
        )


        if recovered_ticket is None:
            raise TicketExecutionClaimError(
                (
                    "Stale support ticket "
                    "execution claim could "
                    "not be recovered."
                )
            )


        return recovered_ticket


    raise TicketExecutionClaimError(
        (
            "Support ticket is not in a "
            "claimable execution state."
        )
    )


# ============================================================
# CLAIM ID
# ============================================================

def get_execution_claim_id(
    *,
    ticket: dict[str, Any],
) -> str:
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
            (
                "Claimed support ticket does "
                "not contain a valid execution "
                "claim ID."
            )
        )


    return (
        execution_claim_id.strip()
    )


# ============================================================
# EXECUTE APPROVED TICKET
# ============================================================

def execute_approved_ticket(
    *,
    ticket_id: str,
) -> dict[str, Any]:
    """
    Safely execute one approved Harbor escalation.

    Flow:

        persisted human approval
                ↓
        tool authorization
                ↓
        atomic execution claim
                ↓
        Monday idempotency lookup
                ↓
        reuse existing / create new
                ↓
        Harbor finalization
                ↓
        return success to staff
                ↓
        background n8n automation

    n8n never determines whether the Monday execution itself
    was successful.
    """

    total_started_at = (
        perf_counter()
    )


    # --------------------------------------------------------
    # 1. AUTHORIZATION
    # --------------------------------------------------------

    authorization_started_at = (
        perf_counter()
    )


    authorized_ticket = (
        authorize_ticket_execution(
            ticket_id=(
                ticket_id
            )
        )
    )


    authorization_ms = (
        _milliseconds(
            authorization_started_at
        )
    )


    # --------------------------------------------------------
    # 2. EXCLUSIVE EXECUTION CLAIM
    # --------------------------------------------------------

    claim_started_at = (
        perf_counter()
    )


    ticket = (
        claim_authorized_ticket(
            ticket=(
                authorized_ticket
            )
        )
    )


    execution_claim_id = (
        get_execution_claim_id(
            ticket=(
                ticket
            )
        )
    )


    claim_ms = (
        _milliseconds(
            claim_started_at
        )
    )


    # --------------------------------------------------------
    # 3. IDEMPOTENCY KEY
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
            (
                "Support ticket does not "
                "contain a valid "
                "idempotency key."
            )
        )


    idempotency_key = (
        idempotency_key.strip()
    )


    # --------------------------------------------------------
    # 4. MONDAY LOOKUP / CREATE
    # --------------------------------------------------------

    monday_started_at = (
        perf_counter()
    )


    reused_existing_item = (
        False
    )


    try:
        monday_item = (
            find_support_ticket_by_idempotency_key(
                idempotency_key=(
                    idempotency_key
                )
            )
        )


        if monday_item is not None:
            reused_existing_item = (
                True
            )


        else:
            monday_item = (
                create_support_ticket_item(
                    title=(
                        ticket[
                            "title"
                        ]
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
                        ticket[
                            "id"
                        ]
                    ),

                    idempotency_key=(
                        idempotency_key
                    ),
                )
            )


    except MondayConfigurationError as exc:
        raise TicketExternalExecutionError(
            (
                "Monday.com integration "
                "is not configured correctly."
            )
        ) from exc


    except MondayAPIError as exc:
        # Harbor intentionally remains executing because
        # the external result may be uncertain.
        raise TicketExternalExecutionError(
            (
                "The approved support ticket "
                "could not be safely synchronized "
                "with Monday.com."
            )
        ) from exc


    monday_ms = (
        _milliseconds(
            monday_started_at
        )
    )


    # --------------------------------------------------------
    # 5. VALIDATE EXTERNAL RESULT
    # --------------------------------------------------------

    monday_item_id = (
        monday_item.get(
            "id"
        )
    )


    if not monday_item_id:
        raise TicketExternalExecutionError(
            (
                "Monday.com did not return "
                "a valid item ID."
            )
        )


    # --------------------------------------------------------
    # 6. FINALIZE HARBOR
    # --------------------------------------------------------

    persistence_started_at = (
        perf_counter()
    )


    executed_ticket = (
        mark_ticket_executed(
            ticket_id=str(
                ticket[
                    "id"
                ]
            ),

            monday_item_id=str(
                monday_item_id
            ),

            execution_claim_id=(
                execution_claim_id
            ),
        )
    )


    persistence_ms = (
        _milliseconds(
            persistence_started_at
        )
    )


    if executed_ticket is None:
        raise TicketExecutionPersistenceError(
            (
                "Monday.com contains the "
                "support item, but Harbor "
                "could not persist the "
                "execution result."
            )
        )


    # --------------------------------------------------------
    # 7. LOG CORE EXECUTION
    # --------------------------------------------------------

    logger.info(
        (
            "Ticket execution completed | "
            "ticket_id=%s | "
            "monday_item_id=%s | "
            "reused_existing=%s | "
            "authorization_ms=%.2f | "
            "claim_ms=%.2f | "
            "monday_ms=%.2f | "
            "persistence_ms=%.2f | "
            "total_core_ms=%.2f"
        ),
        executed_ticket.get(
            "id"
        ),
        monday_item_id,
        reused_existing_item,
        authorization_ms,
        claim_ms,
        monday_ms,
        persistence_ms,
        _milliseconds(
            total_started_at
        ),
    )


    # --------------------------------------------------------
    # 8. START DOWNSTREAM AUTOMATION
    # --------------------------------------------------------
    #
    # Do NOT wait for n8n.
    #
    # At this point:
    #
    #     Monday succeeded
    #     Harbor persistence succeeded
    #
    # The browser can receive success immediately.
    #

    try:
        dispatch_ticket_execution_event(
            executed_ticket
        )


    except Exception:
        # Starting downstream automation must not reverse a
        # successfully completed external execution.
        logger.exception(
            (
                "Ticket execution succeeded but "
                "the n8n background dispatcher "
                "could not start | ticket_id=%s"
            ),
            executed_ticket.get(
                "id"
            ),
        )


    # --------------------------------------------------------
    # 9. RETURN COMPLETED TICKET
    # --------------------------------------------------------

    return executed_ticket