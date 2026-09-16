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
    list_staff_tickets,
    review_ticket,
)
from app.tickets.schemas import (
    TicketApprovalRequest,
    TicketApprovalResult,
    TicketRecord,
)


router = APIRouter(
    prefix="/tickets"
)


# ============================================================
# Staff Ticket Queries
# ============================================================


@router.get(
    "",
    response_model=list[TicketRecord],
)
def list_tickets(
    current_user=Depends(
        require_roles(
            "support_agent",
            "admin",
        )
    ),
):
    """
    Return Harbor's support queue for authorized staff.

    Support agents and administrators may view customer
    escalation tickets regardless of ticket ownership.

    Backend RBAC remains the real security boundary.
    """

    return list_staff_tickets()


@router.get(
    "/{ticket_id}",
    response_model=TicketRecord,
)
def get_ticket(
    ticket_id: UUID,
    current_user=Depends(
        require_roles(
            "support_agent",
            "admin",
        )
    ),
):
    """
    Return one Harbor support ticket for authorized staff.

    Staff users are intentionally allowed to review tickets
    created by customers.
    """

    try:
        return review_ticket(
            ticket_id=str(ticket_id)
        )

    except TicketNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# ============================================================
# Human Approval
# ============================================================


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

    This endpoint only modifies Harbor's internal workflow
    state.

    It does not execute Monday.com or trigger n8n.
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except TicketAlreadyDecidedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


# ============================================================
# Approved Ticket Execution
# ============================================================


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

    Safe execution flow:

        persisted human approval
                ↓
        execution authorization
                ↓
        atomic execution claim
                ↓
        Monday idempotency lookup
                ↓
        reuse or create Monday item
                ↓
        claim-owned finalization
                ↓
        Harbor ticket becomes open
    """

    try:
        return execute_approved_ticket(
            ticket_id=str(ticket_id)
        )

    except TicketExecutionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except (
        TicketNotApprovedForExecutionError,
        TicketAlreadyExecutedError,
        TicketExecutionClaimError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except TicketExternalExecutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    except TicketExecutionPersistenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc