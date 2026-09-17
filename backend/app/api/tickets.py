import logging
from time import perf_counter
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from fastapi.concurrency import (
    run_in_threadpool,
)

from app.dependencies.auth import (
    require_roles,
)

from app.realtime.manager import (
    notification_manager,
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
    UnsafeTicketContentError,
    create_customer_ticket_reply,
    create_staff_ticket_update,
    decide_ticket_approval,
    get_staff_ticket_for_update,
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


logger = logging.getLogger(
    "harbor.tickets_api"
)


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
# CUSTOMER — LIST CASES
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
    return list_user_tickets(
        user_id=str(
            current_user[
                "id"
            ]
        ),
        limit=100,
    )


# ============================================================
# CUSTOMER — CASE UPDATES
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
    try:
        return (
            list_customer_ticket_updates(
                ticket_id=str(
                    ticket_id
                ),

                user_id=str(
                    current_user[
                        "id"
                    ]
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


# ============================================================
# CUSTOMER — SEND REPLY + REALTIME PUSH
# ============================================================

@router.post(
    "/mine/{ticket_id}/updates",
    response_model=TicketUpdateRecord,
    status_code=(
        status.HTTP_201_CREATED
    ),
)
async def reply_to_my_ticket(
    ticket_id: UUID,
    payload: TicketUpdateRequest,
    current_user=Depends(
        require_roles(
            "customer",
        )
    ),
):
    """
    Optimized customer message path.

    Before:
        ticket lookup
        guardrail
        insert
        author profile lookup
        second ticket lookup
        WebSocket push

    Now:
        one ticket lookup
        guardrail
        insert
        author built from current_user
        WebSocket push
    """

    total_started_at = (
        perf_counter()
    )


    try:
        ticket_id_str = str(
            ticket_id
        )


        user_id = str(
            current_user[
                "id"
            ]
        )


        # ----------------------------------------------------
        # 1. OWNERSHIP CHECK — ONCE
        # ----------------------------------------------------

        lookup_started_at = (
            perf_counter()
        )


        ticket = (
            await run_in_threadpool(
                get_user_ticket,

                ticket_id=(
                    ticket_id_str
                ),

                user_id=user_id,
            )
        )


        lookup_duration = (
            _milliseconds(
                lookup_started_at
            )
        )


        if ticket is None:
            raise TicketNotFoundError(
                "Support ticket was not found."
            )


        # ----------------------------------------------------
        # 2. CREATE UPDATE
        #
        # Pass both ticket and authenticated user so service
        # does NOT query either of them again.
        # ----------------------------------------------------

        create_started_at = (
            perf_counter()
        )


        update = (
            await run_in_threadpool(
                create_customer_ticket_reply,

                ticket_id=(
                    ticket_id_str
                ),

                user_id=user_id,

                content=(
                    payload.content
                ),

                ticket=ticket,

                author_profile=(
                    current_user
                ),
            )
        )


        create_duration = (
            _milliseconds(
                create_started_at
            )
        )


        # ----------------------------------------------------
        # 3. REALTIME PUSH
        # ----------------------------------------------------

        websocket_started_at = (
            perf_counter()
        )


        await notification_manager.send_to_staff(
            payload={
                "type":
                    "ticket_message",

                "recipient":
                    "staff",

                "id":
                    update.get(
                        "id"
                    ),

                "ticket_id":
                    ticket_id_str,

                "update_type":
                    "customer_reply",

                "content":
                    update.get(
                        "content"
                    ),

                "created_at":
                    update.get(
                        "created_at"
                    ),

                "author":
                    update.get(
                        "author"
                    ),

                "ticket": {
                    "id":
                        ticket.get(
                            "id"
                        ),

                    "title":
                        ticket.get(
                            "title"
                        ),

                    "status":
                        ticket.get(
                            "status"
                        ),

                    "approval_status":
                        ticket.get(
                            "approval_status"
                        ),

                    "severity":
                        ticket.get(
                            "severity"
                        ),

                    "user_id":
                        ticket.get(
                            "user_id"
                        ),
                },
            }
        )


        websocket_duration = (
            _milliseconds(
                websocket_started_at
            )
        )


        logger.info(
            (
                "Customer reply request completed | "
                "ticket_id=%s | "
                "lookup_ms=%.2f | "
                "create_ms=%.2f | "
                "websocket_ms=%.2f | "
                "total_ms=%.2f"
            ),
            ticket_id_str,
            lookup_duration,
            create_duration,
            websocket_duration,
            _milliseconds(
                total_started_at
            ),
        )


        return update


    except TicketNotFoundError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),

            detail=str(
                exc
            ),
        ) from exc


    except (
        UnsafeTicketContentError,
        ValueError,
        TypeError,
    ) as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=str(
                exc
            ),
        ) from exc


# ============================================================
# CUSTOMER — GET CASE
# ============================================================

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
    ticket = (
        get_user_ticket(
            ticket_id=str(
                ticket_id
            ),

            user_id=str(
                current_user[
                    "id"
                ]
            ),
        )
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
# STAFF — LIST ALL TICKETS
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
    return list_staff_tickets(
        limit=100,
    )


# ============================================================
# STAFF — GET TIMELINE
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


# ============================================================
# STAFF — REPLY / INTERNAL NOTE
# ============================================================

@router.post(
    "/{ticket_id}/updates",
    response_model=TicketUpdateRecord,
    status_code=(
        status.HTTP_201_CREATED
    ),
)
async def create_staff_update(
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
    Optimized staff message path.

    The ticket is fetched only once.

    The authenticated staff profile is reused rather than
    querying the users table again.

    Internal notes still NEVER emit a customer WebSocket
    event.
    """

    total_started_at = (
        perf_counter()
    )


    try:
        ticket_id_str = str(
            ticket_id
        )


        # ----------------------------------------------------
        # 1. TICKET CHECK — ONCE
        # ----------------------------------------------------

        lookup_started_at = (
            perf_counter()
        )


        ticket = (
            await run_in_threadpool(
                get_staff_ticket_for_update,

                ticket_id=(
                    ticket_id_str
                ),
            )
        )


        lookup_duration = (
            _milliseconds(
                lookup_started_at
            )
        )


        # ----------------------------------------------------
        # 2. CREATE UPDATE
        #
        # No additional ticket lookup.
        # No additional staff profile lookup.
        # ----------------------------------------------------

        create_started_at = (
            perf_counter()
        )


        update = (
            await run_in_threadpool(
                create_staff_ticket_update,

                ticket_id=(
                    ticket_id_str
                ),

                staff_id=str(
                    current_user[
                        "id"
                    ]
                ),

                staff_role=str(
                    current_user[
                        "role"
                    ]
                ),

                update_type=(
                    payload.update_type
                ),

                content=(
                    payload.content
                ),

                ticket=ticket,

                author_profile=(
                    current_user
                ),
            )
        )


        create_duration = (
            _milliseconds(
                create_started_at
            )
        )


        websocket_duration = (
            0.0
        )


        # ----------------------------------------------------
        # 3. CUSTOMER REALTIME PUSH
        #
        # Absolutely nothing is emitted for internal_note.
        # ----------------------------------------------------

        if (
            payload.update_type
            == "staff_reply"
        ):
            websocket_started_at = (
                perf_counter()
            )


            customer_id = str(
                ticket[
                    "user_id"
                ]
            )


            await notification_manager.send_to_customer(
                user_id=customer_id,

                payload={
                    "type":
                        "ticket_message",

                    "recipient":
                        "customer",

                    "id":
                        update.get(
                            "id"
                        ),

                    "ticket_id":
                        ticket_id_str,

                    "update_type":
                        "staff_reply",

                    "content":
                        update.get(
                            "content"
                        ),

                    "created_at":
                        update.get(
                            "created_at"
                        ),

                    "author":
                        update.get(
                            "author"
                        ),

                    "ticket": {
                        "id":
                            ticket.get(
                                "id"
                            ),

                        "title":
                            ticket.get(
                                "title"
                            ),

                        "status":
                            ticket.get(
                                "status"
                            ),

                        "approval_status":
                            ticket.get(
                                "approval_status"
                            ),

                        "severity":
                            ticket.get(
                                "severity"
                            ),

                        "user_id":
                            ticket.get(
                                "user_id"
                            ),
                    },
                },
            )


            websocket_duration = (
                _milliseconds(
                    websocket_started_at
                )
            )


        logger.info(
            (
                "Staff update request completed | "
                "ticket_id=%s | "
                "type=%s | "
                "lookup_ms=%.2f | "
                "create_ms=%.2f | "
                "websocket_ms=%.2f | "
                "total_ms=%.2f"
            ),
            ticket_id_str,
            payload.update_type,
            lookup_duration,
            create_duration,
            websocket_duration,
            _milliseconds(
                total_started_at
            ),
        )


        return update


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


    except (
        UnsafeTicketContentError,
        ValueError,
        TypeError,
    ) as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=str(
                exc
            ),
        ) from exc


# ============================================================
# STAFF — GET ONE TICKET
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
# STAFF — APPROVAL
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
    try:
        return (
            decide_ticket_approval(
                ticket_id=str(
                    ticket_id
                ),

                reviewer_id=str(
                    current_user[
                        "id"
                    ]
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
# STAFF — EXECUTE APPROVED TICKET
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