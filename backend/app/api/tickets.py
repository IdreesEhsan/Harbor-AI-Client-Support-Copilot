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
    InvalidTicketUpdateTypeError,
    TicketAlreadyDecidedError,
    TicketNotFoundError,
    create_customer_ticket_reply,
    create_staff_ticket_update,
    decide_ticket_approval,
    get_user_ticket,
    list_customer_ticket_updates,
    list_staff_ticket_updates,
    list_staff_tickets,
    list_user_tickets,
    review_ticket,
)

from app.tickets.schemas import (
    StaffTicketUpdateRequest,
    TicketApprovalRequest,
    TicketApprovalResult,
    TicketRecord,
    TicketUpdateRecord,
    TicketUpdateRequest,
)


router = APIRouter(
    prefix="/tickets"
)


# ============================================================
# CUSTOMER — MY CASES
# ============================================================

@router.get(
    "/mine",
    response_model=list[
        TicketRecord
    ],
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
    """

    return list_user_tickets(
        user_id=str(
            current_user["id"]
        ),
        limit=100,
    )


# ============================================================
# CUSTOMER — CASE CONVERSATION
# ============================================================

@router.get(
    "/mine/{ticket_id}/updates",
    response_model=list[
        TicketUpdateRecord
    ],
)
def get_my_ticket_updates(
    ticket_id: UUID,
    current_user=Depends(
        require_roles(
            "customer",
        )
    ),
):
    """
    Return customer-visible conversation entries for one
    customer-owned support ticket.

    Internal notes are never returned.
    """

    try:
        return (
            list_customer_ticket_updates(
                ticket_id=str(
                    ticket_id
                ),

                user_id=str(
                    current_user["id"]
                ),
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


@router.post(
    "/mine/{ticket_id}/updates",
    response_model=TicketUpdateRecord,
    status_code=(
        status.HTTP_201_CREATED
    ),
)
def reply_to_my_ticket(
    ticket_id: UUID,
    payload: TicketUpdateRequest,
    current_user=Depends(
        require_roles(
            "customer",
        )
    ),
):
    """
    Add one customer reply to an owned support ticket.
    """

    try:
        return (
            create_customer_ticket_reply(
                ticket_id=str(
                    ticket_id
                ),

                user_id=str(
                    current_user["id"]
                ),

                content=(
                    payload.content
                ),
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
    response_model=list[
        TicketRecord
    ],
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
    Return all Harbor support tickets visible to staff.
    """

    return list_staff_tickets(
        limit=100,
    )


# ============================================================
# STAFF — TICKET CONVERSATION
# ============================================================

@router.get(
    "/{ticket_id}/updates",
    response_model=list[
        TicketUpdateRecord
    ],
)
def get_staff_ticket_updates(
    ticket_id: UUID,
    current_user=Depends(
        require_roles(
            "support_agent",
            "admin",
        )
    ),
):
    """
    Return complete staff ticket timeline.

    Includes internal notes.
    """

    try:
        return (
            list_staff_ticket_updates(
                ticket_id=str(
                    ticket_id
                )
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


@router.post(
    "/{ticket_id}/updates",
    response_model=TicketUpdateRecord,
    status_code=(
        status.HTTP_201_CREATED
    ),
)
def create_staff_update(
    ticket_id: UUID,
    payload: StaffTicketUpdateRequest,
    current_user=Depends(
        require_roles(
            "support_agent",
            "admin",
        )
    ),
):
    """
    Add either:

    - customer-visible staff reply;
    - staff-only internal note.
    """

    try:
        return (
            create_staff_ticket_update(
                ticket_id=str(
                    ticket_id
                ),

                staff_id=str(
                    current_user["id"]
                ),

                staff_role=str(
                    current_user["role"]
                ),

                update_type=(
                    payload.update_type
                ),

                content=(
                    payload.content
                ),
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

    except InvalidTicketUpdateTypeError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=str(
                exc
            ),
        ) from exc


# ============================================================
# STAFF — SINGLE TICKET
# ============================================================

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

    Approval changes Harbor's internal state only.
    """

    try:
        return (
            decide_ticket_approval(
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
    """

    try:
        return (
            execute_approved_ticket(
                ticket_id=str(
                    ticket_id
                )
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