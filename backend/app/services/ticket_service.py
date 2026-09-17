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


# ============================================================
# EXCEPTIONS
# ============================================================

class TicketConversationNotFoundError(
    Exception
):
    """
    Conversation does not exist or does not belong to the
    authenticated customer.
    """


class UnsafeTicketContentError(
    Exception
):
    """
    Ticket content failed Harbor's safety checks.
    """


class TicketNotFoundError(
    Exception
):
    """
    Requested support ticket does not exist.
    """


class TicketAlreadyDecidedError(
    Exception
):
    """
    Ticket approval decision has already been made.
    """


class InvalidTicketUpdateTypeError(
    Exception
):
    """
    Unsupported ticket update type.
    """


# ============================================================
# CONTENT SAFETY
# ============================================================

def prepare_ticket_content(
    content: str,
) -> str:
    """
    Run persisted support content through Harbor's input
    guardrails before storing it.
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
            raise (
                UnsafeTicketContentError(
                    "Ticket content could not "
                    "be sanitized safely."
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
    Build deterministic internal ticket identity.
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
    """
    Validate and persist a customer-confirmed escalation.

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
    Return authenticated customer's support tickets.
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
    Attach safe customer profile information to a
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
    Enrich staff ticket list using one batched profile
    lookup.
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
    Return all tickets for authorized Harbor staff.
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
    Load one ticket for authorized support staff.
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
    Persist an authorized staff approval or rejection.

    This operation does not execute external business
    actions.
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


# ============================================================
# TICKET UPDATE AUTHOR ENRICHMENT
# ============================================================

def enrich_ticket_updates(
    updates: list[
        dict[str, Any]
    ],
) -> list[
    dict[str, Any]
]:
    """
    Attach safe profile data to ticket update authors.
    """

    if not updates:
        return []

    author_ids = [
        str(
            update["author_id"]
        )
        for update
        in updates
        if update.get(
            "author_id"
        )
    ]

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

        profile = profiles.get(
            author_id
        )

        if profile:
            record[
                "author"
            ] = {
                "id":
                    profile["id"],

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

        else:
            record[
                "author"
            ] = {
                "id":
                    author_id,

                "full_name":
                    None,

                "email":
                    None,

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
) -> dict[str, Any]:
    """
    Create a customer reply on a customer-owned ticket.
    """

    ticket = get_user_ticket(
        ticket_id=ticket_id,
        user_id=user_id,
    )

    if ticket is None:
        raise TicketNotFoundError(
            "Support ticket was not found."
        )

    safe_content = (
        prepare_ticket_content(
            content
        )
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

    return (
        enrich_ticket_updates(
            [update]
        )[0]
    )


def list_customer_ticket_updates(
    *,
    ticket_id: str,
    user_id: str,
) -> list[dict[str, Any]]:
    """
    Return customer-visible timeline entries for one
    customer-owned ticket.

    Internal notes never leave this method.
    """

    ticket = get_user_ticket(
        ticket_id=ticket_id,
        user_id=user_id,
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
) -> dict[str, Any]:
    """
    Create either:

    - customer-visible staff reply;
    - staff-only internal note.
    """

    if update_type not in {
        "staff_reply",
        "internal_note",
    }:
        raise (
            InvalidTicketUpdateTypeError(
                "Unsupported staff update type."
            )
        )

    review_ticket(
        ticket_id=ticket_id
    )

    safe_content = (
        prepare_ticket_content(
            content
        )
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

    return (
        enrich_ticket_updates(
            [update]
        )[0]
    )


def list_staff_ticket_updates(
    *,
    ticket_id: str,
) -> list[dict[str, Any]]:
    """
    Return complete support timeline for authorized staff.

    Includes internal notes.
    """

    review_ticket(
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