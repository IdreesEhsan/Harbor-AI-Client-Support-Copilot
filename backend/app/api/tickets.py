from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from app.dependencies.auth import require_roles
from app.services.ticket_service import (
    TicketAlreadyDecidedError,
    TicketNotFoundError,
    decide_ticket_approval,
)
from app.tickets.schemas import (
    TicketApprovalRequest,
    TicketApprovalResult,
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except TicketAlreadyDecidedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc