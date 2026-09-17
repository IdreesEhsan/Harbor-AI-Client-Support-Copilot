import hashlib
import logging
from time import perf_counter
from typing import Any
from uuid import UUID

from app.guardrails.pipeline import (
    run_input_guardrails,
)

from app.repositories.conversations import (
    get_conversation,
)

from app.repositories.ticket_repository import (
    approve_ticket,
    create_ticket,
    create_ticket_update,
    get_customer_profile,
    get_customer_profiles,
    get_ticket,
    get_ticket_for_review,
    list_all_ticket_updates,
    list_all_tickets,
    list_customer_visible_ticket_updates,
    list_tickets,
    reject_ticket,
)

from app.tickets.schemas import (
    TicketApprovalResult,
    TicketCreate,
    TicketSeverity,
)


logger = logging.getLogger(
    "harbor.ticket_service"
)


# ============================================================
# EXCEPTIONS
# ============================================================

class TicketConversationNotFoundError(
    Exception
):
    pass


class UnsafeTicketContentError(
    Exception
):
    pass


class TicketNotFoundError(
    Exception
):
    pass


class TicketAlreadyDecidedError(
    Exception
):
    pass


class InvalidTicketUpdateTypeError(
    Exception
):
    pass


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
# CONTENT SAFETY
# ============================================================

def prepare_ticket_content(
    content: str,
) -> str:
    """
    Validate and sanitize ticket/update content.

    Guardrails are intentionally preserved. If message
    latency remains after the database optimizations, the
    timing logs around this function will show whether the
    guardrail pipeline is the expensive part.
    """

    if not isinstance(
        content,
        str,
    ):
        raise TypeError(
            "Ticket content must be a string."
        )

    content = content.strip()

    if not content:
        raise ValueError(
            "Ticket content cannot be empty."
        )


    started_at = (
        perf_counter()
    )


    result = (
        run_input_guardrails(
            content
        )
    )


    logger.info(
        (
            "Ticket guardrail completed | "
            "status=%s | duration_ms=%.2f"
        ),
        result.status,
        _milliseconds(
            started_at
        ),
    )


    if result.status == "allow":
        return content


    if result.status == "redact":
        safe_content = (
            result.redacted_content
            or ""
        ).strip()

        if not safe_content:
            raise UnsafeTicketContentError(
                (
                    "Ticket content could not "
                    "be sanitized safely."
                )
            )

        return safe_content


    if result.status == "escalate":
        safe_content = (
            result.redacted_content
            or content
        ).strip()

        if not safe_content:
            raise UnsafeTicketContentError(
                (
                    "Ticket content could not "
                    "be sanitized safely."
                )
            )

        return safe_content


    if result.status == "block":
        raise UnsafeTicketContentError(
            (
                "Ticket content was blocked "
                "by Harbor's guardrails."
            )
        )


    raise UnsafeTicketContentError(
        (
            "Ticket content could not "
            "be validated safely."
        )
    )


# ============================================================
# IDEMPOTENCY
# ============================================================

def build_ticket_idempotency_key(
    *,
    user_id: str,
    conversation_id: str,
    title: str,
    description: str,
) -> str:
    normalized = "|".join(
        [
            user_id.strip(),
            conversation_id.strip(),
            title.strip(),
            description.strip(),
        ]
    )


    digest = (
        hashlib.sha256(
            normalized.encode(
                "utf-8"
            )
        ).hexdigest()
    )


    return (
        f"harbor-ticket-{digest}"
    )


# ============================================================
# CREATE SUPPORT TICKET
# ============================================================

def prepare_support_ticket(
    *,
    user_id: str,
    conversation_id: str,
    title: str,
    description: str,
    severity: TicketSeverity = "medium",
) -> dict[str, Any]:
    conversation = (
        get_conversation(
            conversation_id=(
                conversation_id
            ),
            user_id=user_id,
        )
    )


    if conversation is None:
        raise TicketConversationNotFoundError(
            "Conversation was not found."
        )


    safe_title = (
        prepare_ticket_content(
            title
        )
    )


    safe_description = (
        prepare_ticket_content(
            description
        )
    )


    idempotency_key = (
        build_ticket_idempotency_key(
            user_id=user_id,
            conversation_id=(
                conversation_id
            ),
            title=safe_title,
            description=(
                safe_description
            ),
        )
    )


    ticket = TicketCreate(
        user_id=UUID(
            user_id
        ),

        conversation_id=UUID(
            conversation_id
        ),

        title=safe_title,

        description=(
            safe_description
        ),

        severity=severity,

        idempotency_key=(
            idempotency_key
        ),
    )


    return create_ticket(
        ticket
    )


# ============================================================
# CUSTOMER TICKET ACCESS
# ============================================================

def get_user_ticket(
    *,
    ticket_id: str,
    user_id: str,
) -> dict[str, Any] | None:
    return get_ticket(
        ticket_id=ticket_id,
        user_id=user_id,
    )


def list_user_tickets(
    *,
    user_id: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    return list_tickets(
        user_id=user_id,
        limit=limit,
    )


# ============================================================
# STAFF TICKET ACCESS
# ============================================================

def get_staff_ticket_for_update(
    *,
    ticket_id: str,
) -> dict[str, Any]:
    """
    Lightweight staff ticket lookup.

    Unlike review_ticket(), this does NOT query the customer's
    profile because sending a message only needs the ticket
    record itself.

    This removes a database query from every staff message.
    """

    ticket = (
        get_ticket_for_review(
            ticket_id
        )
    )


    if ticket is None:
        raise TicketNotFoundError(
            "Support ticket was not found."
        )


    return ticket


# ============================================================
# STAFF CUSTOMER ENRICHMENT
# ============================================================

def enrich_ticket_with_customer(
    ticket: dict[str, Any],
) -> dict[str, Any]:
    enriched_ticket = dict(
        ticket
    )


    customer = None


    user_id = (
        ticket.get(
            "user_id"
        )
    )


    if user_id:
        customer = (
            get_customer_profile(
                str(
                    user_id
                )
            )
        )


    enriched_ticket[
        "customer"
    ] = customer


    return enriched_ticket


def enrich_tickets_with_customers(
    tickets: list[
        dict[str, Any]
    ],
) -> list[
    dict[str, Any]
]:
    if not tickets:
        return []


    user_ids = [
        str(
            ticket[
                "user_id"
            ]
        )
        for ticket
        in tickets
        if ticket.get(
            "user_id"
        )
    ]


    profiles = (
        get_customer_profiles(
            user_ids
        )
    )


    enriched_tickets = []


    for ticket in tickets:
        enriched_ticket = dict(
            ticket
        )


        user_id = str(
            ticket.get(
                "user_id",
                "",
            )
        )


        enriched_ticket[
            "customer"
        ] = profiles.get(
            user_id
        )


        enriched_tickets.append(
            enriched_ticket
        )


    return enriched_tickets


def list_staff_tickets(
    *,
    limit: int = 100,
) -> list[
    dict[str, Any]
]:
    tickets = (
        list_all_tickets(
            limit=limit
        )
    )


    return (
        enrich_tickets_with_customers(
            tickets
        )
    )


def review_ticket(
    *,
    ticket_id: str,
) -> dict[str, Any]:
    ticket = (
        get_staff_ticket_for_update(
            ticket_id=(
                ticket_id
            )
        )
    )


    return (
        enrich_ticket_with_customer(
            ticket
        )
    )


# ============================================================
# HUMAN APPROVAL
# ============================================================

def decide_ticket_approval(
    *,
    ticket_id: str,
    reviewer_id: str,
    approved: bool,
) -> TicketApprovalResult:
    ticket = (
        review_ticket(
            ticket_id=ticket_id
        )
    )


    if (
        ticket.get(
            "approval_status"
        )
        != "pending"
        or ticket.get(
            "status"
        )
        != "pending_approval"
    ):
        raise TicketAlreadyDecidedError(
            (
                "Support ticket has "
                "already been decided."
            )
        )


    if approved:
        updated_ticket = (
            approve_ticket(
                ticket_id=(
                    ticket_id
                ),
                approved_by=(
                    reviewer_id
                ),
            )
        )

    else:
        updated_ticket = (
            reject_ticket(
                ticket_id=(
                    ticket_id
                ),
                rejected_by=(
                    reviewer_id
                ),
            )
        )


    if updated_ticket is None:
        raise TicketAlreadyDecidedError(
            (
                "Support ticket has "
                "already been decided."
            )
        )


    return TicketApprovalResult(
        ticket_id=(
            updated_ticket[
                "id"
            ]
        ),

        approval_status=(
            updated_ticket[
                "approval_status"
            ]
        ),

        status=(
            updated_ticket[
                "status"
            ]
        ),

        approved_by=(
            updated_ticket.get(
                "approved_by"
            )
        ),

        approved_at=(
            updated_ticket.get(
                "approved_at"
            )
        ),
    )


# ============================================================
# AUTHOR BUILDING
# ============================================================

def build_update_author(
    *,
    author_id: str,
    author_role: str,
    author_profile: dict[
        str,
        Any
    ] | None = None,
) -> dict[str, Any]:
    """
    Build the author object without another database query
    when the API already has the authenticated user.

    For newly-created messages, current_user already contains
    the required identity fields.
    """

    profile = (
        author_profile
        or {}
    )


    return {
        "id":
            str(
                profile.get(
                    "id"
                )
                or author_id
            ),

        "full_name":
            profile.get(
                "full_name"
            ),

        "email":
            profile.get(
                "email"
            ),

        "role":
            author_role,
    }


def attach_update_author(
    *,
    update: dict[str, Any],
    author_id: str,
    author_role: str,
    author_profile: dict[
        str,
        Any
    ] | None = None,
) -> dict[str, Any]:
    record = dict(
        update
    )


    record[
        "author"
    ] = (
        build_update_author(
            author_id=author_id,
            author_role=author_role,
            author_profile=(
                author_profile
            ),
        )
    )


    return record


# ============================================================
# UPDATE AUTHOR ENRICHMENT
# ============================================================

def enrich_ticket_updates(
    updates: list[
        dict[str, Any]
    ],
) -> list[
    dict[str, Any]
]:
    """
    Used when loading historical timelines.

    Batch enrichment is still appropriate here because the
    API does not already have every message author's profile.
    """

    if not updates:
        return []


    author_ids = list(
        {
            str(
                update[
                    "author_id"
                ]
            )
            for update
            in updates
            if update.get(
                "author_id"
            )
        }
    )


    profiles = (
        get_customer_profiles(
            author_ids
        )
    )


    enriched = []


    for update in updates:
        record = dict(
            update
        )


        author_id = str(
            update.get(
                "author_id",
                "",
            )
        )


        profile = (
            profiles.get(
                author_id
            )
            or {}
        )


        record[
            "author"
        ] = {
            "id":
                author_id,

            "full_name":
                profile.get(
                    "full_name"
                ),

            "email":
                profile.get(
                    "email"
                ),

            "role":
                update.get(
                    "author_role"
                ),
        }


        enriched.append(
            record
        )


    return enriched


# ============================================================
# CUSTOMER REPLIES
# ============================================================

def create_customer_ticket_reply(
    *,
    ticket_id: str,
    user_id: str,
    content: str,
    ticket: dict[
        str,
        Any
    ] | None = None,
    author_profile: dict[
        str,
        Any
    ] | None = None,
) -> dict[str, Any]:
    """
    Create a customer reply.

    Optimized route:
        API fetches/validates ticket once and passes it here.

    Compatibility:
        If no ticket is supplied, this function still performs
        the ownership check itself.
    """

    total_started_at = (
        perf_counter()
    )


    if ticket is None:
        lookup_started_at = (
            perf_counter()
        )


        ticket = (
            get_user_ticket(
                ticket_id=ticket_id,
                user_id=user_id,
            )
        )


        logger.info(
            (
                "Customer reply ticket lookup | "
                "ticket_id=%s | duration_ms=%.2f"
            ),
            ticket_id,
            _milliseconds(
                lookup_started_at
            ),
        )


    if ticket is None:
        raise TicketNotFoundError(
            "Support ticket was not found."
        )


    guardrail_started_at = (
        perf_counter()
    )


    safe_content = (
        prepare_ticket_content(
            content
        )
    )


    guardrail_duration = (
        _milliseconds(
            guardrail_started_at
        )
    )


    insert_started_at = (
        perf_counter()
    )


    update = (
        create_ticket_update(
            ticket_id=ticket_id,
            author_id=user_id,
            author_role="customer",
            update_type=(
                "customer_reply"
            ),
            content=safe_content,
        )
    )


    insert_duration = (
        _milliseconds(
            insert_started_at
        )
    )


    result = (
        attach_update_author(
            update=update,
            author_id=user_id,
            author_role="customer",
            author_profile=(
                author_profile
            ),
        )
    )


    logger.info(
        (
            "Customer reply created | "
            "ticket_id=%s | "
            "guardrail_ms=%.2f | "
            "insert_ms=%.2f | "
            "total_ms=%.2f"
        ),
        ticket_id,
        guardrail_duration,
        insert_duration,
        _milliseconds(
            total_started_at
        ),
    )


    return result


def list_customer_ticket_updates(
    *,
    ticket_id: str,
    user_id: str,
) -> list[
    dict[str, Any]
]:
    ticket = (
        get_user_ticket(
            ticket_id=ticket_id,
            user_id=user_id,
        )
    )


    if ticket is None:
        raise TicketNotFoundError(
            "Support ticket was not found."
        )


    updates = (
        list_customer_visible_ticket_updates(
            ticket_id
        )
    )


    return (
        enrich_ticket_updates(
            updates
        )
    )


# ============================================================
# STAFF REPLIES / INTERNAL NOTES
# ============================================================

def create_staff_ticket_update(
    *,
    ticket_id: str,
    staff_id: str,
    staff_role: str,
    update_type: str,
    content: str,
    ticket: dict[
        str,
        Any
    ] | None = None,
    author_profile: dict[
        str,
        Any
    ] | None = None,
) -> dict[str, Any]:
    """
    Create a staff reply/internal note without performing
    redundant ticket/profile lookups when the route already
    has those records.
    """

    if update_type not in {
        "staff_reply",
        "internal_note",
    }:
        raise InvalidTicketUpdateTypeError(
            "Unsupported staff update type."
        )


    total_started_at = (
        perf_counter()
    )


    if ticket is None:
        lookup_started_at = (
            perf_counter()
        )


        ticket = (
            get_staff_ticket_for_update(
                ticket_id=ticket_id
            )
        )


        logger.info(
            (
                "Staff reply ticket lookup | "
                "ticket_id=%s | duration_ms=%.2f"
            ),
            ticket_id,
            _milliseconds(
                lookup_started_at
            ),
        )


    guardrail_started_at = (
        perf_counter()
    )


    safe_content = (
        prepare_ticket_content(
            content
        )
    )


    guardrail_duration = (
        _milliseconds(
            guardrail_started_at
        )
    )


    insert_started_at = (
        perf_counter()
    )


    update = (
        create_ticket_update(
            ticket_id=ticket_id,
            author_id=staff_id,
            author_role=staff_role,
            update_type=(
                update_type
            ),
            content=safe_content,
        )
    )


    insert_duration = (
        _milliseconds(
            insert_started_at
        )
    )


    result = (
        attach_update_author(
            update=update,
            author_id=staff_id,
            author_role=staff_role,
            author_profile=(
                author_profile
            ),
        )
    )


    logger.info(
        (
            "Staff ticket update created | "
            "ticket_id=%s | "
            "type=%s | "
            "guardrail_ms=%.2f | "
            "insert_ms=%.2f | "
            "total_ms=%.2f"
        ),
        ticket_id,
        update_type,
        guardrail_duration,
        insert_duration,
        _milliseconds(
            total_started_at
        ),
    )


    return result


def list_staff_ticket_updates(
    *,
    ticket_id: str,
) -> list[
    dict[str, Any]
]:
    get_staff_ticket_for_update(
        ticket_id=ticket_id
    )


    updates = (
        list_all_ticket_updates(
            ticket_id
        )
    )


    return (
        enrich_ticket_updates(
            updates
        )
    )