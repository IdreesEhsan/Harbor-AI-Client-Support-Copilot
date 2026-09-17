import hashlib
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
    get_customer_profile,
    get_customer_profiles,
    get_ticket,
    get_ticket_for_review,
    list_all_tickets,
    list_tickets,
    reject_ticket,
)

from app.tickets.schemas import (
    TicketApprovalResult,
    TicketCreate,
    TicketSeverity,
)


# ============================================================
# EXCEPTIONS
# ============================================================

class TicketConversationNotFoundError(
    Exception
):
    """
    Raised when the conversation does not exist or does
    not belong to the authenticated customer.
    """


class UnsafeTicketContentError(
    Exception
):
    """
    Raised when ticket content cannot safely be persisted.
    """


class TicketNotFoundError(
    Exception
):
    """
    Raised when a requested support ticket does not exist.
    """


class TicketAlreadyDecidedError(
    Exception
):
    """
    Raised when a support agent attempts to decide an
    already-decided ticket.
    """


# ============================================================
# CONTENT SAFETY
# ============================================================

def prepare_ticket_content(
    content: str,
) -> str:
    """
    Run ticket content through Harbor input guardrails
    before storing it.
    """

    if not isinstance(
        content,
        str,
    ):
        raise TypeError(
            "Ticket content must be a string."
        )

    content = (
        content.strip()
    )

    if not content:
        raise ValueError(
            "Ticket content cannot be empty."
        )

    result = (
        run_input_guardrails(
            content
        )
    )

    if result.status == "allow":
        return content

    if result.status == "redact":
        safe_content = (
            result.redacted_content
            or ""
        ).strip()

        if not safe_content:
            raise (
                UnsafeTicketContentError(
                    "Ticket content could not be "
                    "sanitized safely."
                )
            )

        return safe_content

    if result.status == "escalate":
        safe_content = (
            result.redacted_content
            or content
        ).strip()

        if not safe_content:
            raise (
                UnsafeTicketContentError(
                    "Ticket content could not be "
                    "sanitized safely."
                )
            )

        return safe_content

    if result.status == "block":
        raise (
            UnsafeTicketContentError(
                "Ticket content was blocked by "
                "Harbor's guardrails."
            )
        )

    raise UnsafeTicketContentError(
        "Ticket content could not be validated safely."
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
    """
    Build deterministic ticket identity without exposing
    raw customer content inside the key.
    """

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
# CREATE TICKET
# ============================================================

def prepare_support_ticket(
    *,
    user_id: str,
    conversation_id: str,
    title: str,
    description: str,
    severity: TicketSeverity = "medium",
) -> dict[str, Any]:
    """
    Validate and persist a confirmed customer escalation.

    This does not approve or execute any external action.
    """

    conversation = (
        get_conversation(
            conversation_id=(
                conversation_id
            ),
            user_id=user_id,
        )
    )

    if conversation is None:
        raise (
            TicketConversationNotFoundError(
                "Conversation was not found."
            )
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
    """
    Return one ticket belonging to an authenticated
    customer.
    """

    return get_ticket(
        ticket_id=ticket_id,
        user_id=user_id,
    )


def list_user_tickets(
    *,
    user_id: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Return customer-owned tickets.

    This will power My Cases.
    """

    return list_tickets(
        user_id=user_id,
        limit=limit,
    )


# ============================================================
# STAFF CUSTOMER ENRICHMENT
# ============================================================

def enrich_ticket_with_customer(
    ticket: dict[str, Any],
) -> dict[str, Any]:
    """
    Add support-relevant customer profile data to one
    staff-facing ticket.
    """

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
                str(user_id)
            )
        )

    enriched_ticket[
        "customer"
    ] = customer

    return enriched_ticket


def enrich_tickets_with_customers(
    tickets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Enrich multiple staff tickets using one batched user
    lookup rather than one database request per ticket.
    """

    if not tickets:
        return []

    user_ids = [
        str(
            ticket["user_id"]
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
        enriched_ticket = (
            dict(ticket)
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
) -> list[dict[str, Any]]:
    """
    Return all customer support tickets for authorized
    staff, enriched with customer profile information.
    """

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
    """
    Load one ticket for an authorized staff member and
    attach the customer's profile information.
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
    """
    Record an authorized staff approval or rejection.

    No external business action occurs in this function.
    """

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
        raise (
            TicketAlreadyDecidedError(
                "Support ticket has already been decided."
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
        raise (
            TicketAlreadyDecidedError(
                "Support ticket has already been decided."
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