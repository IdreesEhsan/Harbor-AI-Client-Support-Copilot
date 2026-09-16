from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from app.dependencies.auth import require_roles
from app.services.ticket_execution_service import (
    TicketAlreadyExecutedError,
    TicketExecutionClaimError,
    TicketExecutionNotFoundError,
    TicketExecutionPersistenceError,
    TicketExternalExecutionError,
    TicketNotApprovedForExecutionError,
    execute_approved_ticket,
)
from app.services.ticket_service import (
    TicketAlreadyDecidedError,
    TicketNotFoundError,
    decide_ticket_approval,
)
from app.tickets.schemas import (
    TicketApprovalRequest,
    TicketApprovalResult,
    TicketRecord,
)


router = APIRouter(
    prefix="/tickets"
)


@router.post(
    "/{ticket_id}/approval",
    response_model=TicketApprovalResult,
)
def decide_ticket(
    ticket_id: UUID,
    payload: TicketApprovalRequest,
    current_user=Depends(
        require_roles(
            "support_agent",
            "admin",
        )
    ),
):
    """
    Approve or reject a pending Harbor support ticket.

    Only authenticated support agents and administrators may
    make this decision.

    This endpoint changes Harbor's internal approval state
    only. It does not execute Monday.com, n8n, notification,
    or other external side effects.
    """

    try:
        return decide_ticket_approval(
            ticket_id=str(ticket_id),
            reviewer_id=str(
                current_user["id"]
            ),
            approved=payload.approved,
        )

    except TicketNotFoundError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=str(exc),
        ) from exc

    except TicketAlreadyDecidedError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=str(exc),
        ) from exc


@router.post(
    "/{ticket_id}/execute",
    response_model=TicketRecord,
)
def execute_ticket(
    ticket_id: UUID,
    current_user=Depends(
        require_roles(
            "support_agent",
            "admin",
        )
    ),
):
    """
    Execute an approved Harbor support ticket.

    Only authenticated support agents and administrators may
    trigger this endpoint.

    Execution is still controlled by Harbor's trusted
    persisted state. Calling this endpoint does not bypass
    human approval.

    Safe execution flow:

        persisted approval
                ↓
        tool authorization
                ↓
        atomic execution claim
                ↓
        Monday idempotency lookup
                ↓
        reuse existing item OR create item
                ↓
        claim-owned finalization
                ↓
        Harbor ticket becomes open

    An executing ticket with an active lease cannot be
    stolen. A stale execution may be recovered through the
    controlled lease-recovery mechanism.
    """

    try:
        return execute_approved_ticket(
            ticket_id=str(ticket_id)
        )

    except TicketExecutionNotFoundError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=str(exc),
        ) from exc

    except (
        TicketNotApprovedForExecutionError,
        TicketAlreadyExecutedError,
        TicketExecutionClaimError,
    ) as exc:
        # These are workflow-state conflicts rather than
        # malformed requests.
        #
        # Examples:
        # - approval has not occurred;
        # - execution already completed;
        # - another worker owns an active lease;
        # - another worker won the claim race.
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=str(exc),
        ) from exc

    except TicketExternalExecutionError as exc:
        # Harbor was allowed to execute, but the external
        # Monday operation could not be completed safely.
        raise HTTPException(
            status_code=(
                status.HTTP_502_BAD_GATEWAY
            ),
            detail=str(exc),
        ) from exc

    except TicketExecutionPersistenceError as exc:
        # Monday may already contain the item, while Harbor
        # failed to finalize its own state.
        #
        # We expose this as a server-side synchronization
        # failure and must not blindly retry an external
        # create operation.
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=str(exc),
        ) from exc