from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from app.dependencies.auth import (
    require_roles,
)

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
    get_user_ticket,
    list_staff_tickets,
    list_user_tickets,
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
# CUSTOMER — MY CASES
# ============================================================

@router.get(
    "/mine",
    response_model=list[TicketRecord],
)
def list_my_tickets(
    current_user=Depends(
        require_roles(
            "customer",
        )
    ),
):
    """
    Return support tickets belonging only to the
    authenticated customer.

    This powers Harbor's My Cases view.
    """

    return list_user_tickets(
        user_id=str(
            current_user["id"]
        ),
        limit=100,
    )


@router.get(
    "/mine/{ticket_id}",
    response_model=TicketRecord,
)
def get_my_ticket(
    ticket_id: UUID,
    current_user=Depends(
        require_roles(
            "customer",
        )
    ),
):
    """
    Return one ticket belonging to the authenticated
    customer.

    Ownership is enforced using both ticket_id and user_id.
    """

    ticket = get_user_ticket(
        ticket_id=str(
            ticket_id
        ),
        user_id=str(
            current_user["id"]
        ),
    )

    if ticket is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "Support ticket was not found."
            ),
        )

    return ticket


# ============================================================
# STAFF — GLOBAL SUPPORT QUEUE
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
    Return all Harbor support tickets visible to
    authorized support staff.
    """

    return list_staff_tickets(
        limit=100,
    )


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
    Return one support ticket for authorized staff review.
    """

    try:
        return review_ticket(
            ticket_id=str(
                ticket_id
            )
        )

    except TicketNotFoundError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=str(
                exc
            ),
        ) from exc


# ============================================================
# STAFF — HUMAN APPROVAL
# ============================================================

@router.post(
    "/{ticket_id}/approval",
    response_model=(
        TicketApprovalResult
    ),
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

    Approval only changes Harbor's internal state.

    It does not execute Monday.com or another external
    business action.
    """

    try:
        return decide_ticket_approval(
            ticket_id=str(
                ticket_id
            ),
            reviewer_id=str(
                current_user["id"]
            ),
            approved=(
                payload.approved
            ),
        )

    except TicketNotFoundError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=str(
                exc
            ),
        ) from exc

    except TicketAlreadyDecidedError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=str(
                exc
            ),
        ) from exc


# ============================================================
# STAFF — APPROVED EXECUTION
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
    Execute a previously approved Harbor support ticket.

    Controlled execution flow:

        human approval
              ↓
        execution authorization
              ↓
        execution claim
              ↓
        Monday.com
              ↓
        Harbor finalization
    """

    try:
        return execute_approved_ticket(
            ticket_id=str(
                ticket_id
            )
        )

    except TicketExecutionNotFoundError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=str(
                exc
            ),
        ) from exc

    except (
        TicketNotApprovedForExecutionError,
        TicketAlreadyExecutedError,
        TicketExecutionClaimError,
    ) as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=str(
                exc
            ),
        ) from exc

    except TicketExternalExecutionError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_502_BAD_GATEWAY
            ),
            detail=str(
                exc
            ),
        ) from exc

    except TicketExecutionPersistenceError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=str(
                exc
            ),
        ) from exc