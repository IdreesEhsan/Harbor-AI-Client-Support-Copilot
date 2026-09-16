import hashlib
from typing import Any
from uuid import UUID

from app.guardrails.pipeline import run_input_guardrails
from app.repositories.conversations import get_conversation
from app.repositories.ticket_repository import (
    approve_ticket,
    create_ticket,
    get_ticket,
    get_ticket_for_review,
    list_tickets,
    list_tickets_for_review,
    reject_ticket,
)
from app.tickets.schemas import (
    TicketApprovalResult,
    TicketCreate,
    TicketSeverity,
)


class TicketConversationNotFoundError(Exception):
    """
    Raised when the target conversation does not exist or
    does not belong to the authenticated user.
    """


class UnsafeTicketContentError(Exception):
    """
    Raised when Harbor refuses to persist unsafe ticket
    content.
    """


class TicketNotFoundError(Exception):
    """
    Raised when a support ticket cannot be found.
    """


class TicketAlreadyDecidedError(Exception):
    """
    Raised when an approval decision is attempted on a ticket
    that is no longer pending human approval.
    """


def prepare_ticket_content(
    content: str,
) -> str:
    """
    Sanitize ticket text before persistence.
    """

    if not isinstance(content, str):
        raise TypeError(
            "Ticket content must be a string."
        )

    content = content.strip()

    if not content:
        raise ValueError(
            "Ticket content cannot be empty."
        )

    result = run_input_guardrails(
        content
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
                "Ticket content could not be "
                "sanitized safely."
            )

        return safe_content

    if result.status == "escalate":
        safe_content = (
            result.redacted_content
            or content
        ).strip()

        if not safe_content:
            raise UnsafeTicketContentError(
                "Ticket content could not be "
                "sanitized safely."
            )

        return safe_content

    if result.status == "block":
        raise UnsafeTicketContentError(
            "Ticket content was blocked by "
            "Harbor's guardrails."
        )

    raise UnsafeTicketContentError(
        "Ticket content could not be validated safely."
    )


def build_ticket_idempotency_key(
    *,
    user_id: str,
    conversation_id: str,
    title: str,
    description: str,
) -> str:
    """
    Build a deterministic idempotency key for one logical
    escalation request.
    """

    normalized = "|".join(
        [
            user_id.strip(),
            conversation_id.strip(),
            title.strip(),
            description.strip(),
        ]
    )

    digest = hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()

    return f"harbor-ticket-{digest}"


def prepare_support_ticket(
    *,
    user_id: str,
    conversation_id: str,
    title: str,
    description: str,
    severity: TicketSeverity = "medium",
) -> dict[str, Any]:
    """
    Prepare and persist an internal Harbor escalation ticket.

    This operation does not approve or externally execute the
    ticket.
    """

    conversation = get_conversation(
        conversation_id=conversation_id,
        user_id=user_id,
    )

    if conversation is None:
        raise TicketConversationNotFoundError(
            "Conversation was not found."
        )

    safe_title = prepare_ticket_content(
        title
    )

    safe_description = prepare_ticket_content(
        description
    )

    idempotency_key = (
        build_ticket_idempotency_key(
            user_id=user_id,
            conversation_id=conversation_id,
            title=safe_title,
            description=safe_description,
        )
    )

    ticket = TicketCreate(
        user_id=UUID(user_id),
        conversation_id=UUID(
            conversation_id
        ),
        title=safe_title,
        description=safe_description,
        severity=severity,
        idempotency_key=idempotency_key,
    )

    return create_ticket(
        ticket
    )


def get_user_ticket(
    *,
    ticket_id: str,
    user_id: str,
) -> dict[str, Any] | None:
    """
    Return one ticket owned by the authenticated customer.
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
    Return tickets belonging to the authenticated customer.
    """

    return list_tickets(
        user_id=user_id,
        limit=limit,
    )


def list_staff_tickets(
    *,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """
    Return Harbor's staff support queue.

    Role authorization must be enforced by the FastAPI API
    boundary before this service function is called.
    """

    return list_tickets_for_review(
        limit=limit,
    )


def review_ticket(
    *,
    ticket_id: str,
) -> dict[str, Any]:
    """
    Load one support ticket for an authorized human reviewer.
    """

    ticket = get_ticket_for_review(
        ticket_id
    )

    if ticket is None:
        raise TicketNotFoundError(
            "Support ticket was not found."
        )

    return ticket


def decide_ticket_approval(
    *,
    ticket_id: str,
    reviewer_id: str,
    approved: bool,
) -> TicketApprovalResult:
    """
    Record a human approval or rejection decision.

    Only tickets that remain pending human approval may be
    decided.
    """

    ticket = review_ticket(
        ticket_id=ticket_id
    )

    if (
        ticket.get("approval_status") != "pending"
        or ticket.get("status") != "pending_approval"
    ):
        raise TicketAlreadyDecidedError(
            "Support ticket has already been decided."
        )

    if approved:
        updated_ticket = approve_ticket(
            ticket_id=ticket_id,
            approved_by=reviewer_id,
        )
    else:
        updated_ticket = reject_ticket(
            ticket_id=ticket_id,
            rejected_by=reviewer_id,
        )

    if updated_ticket is None:
        raise TicketAlreadyDecidedError(
            "Support ticket has already been decided."
        )

    return TicketApprovalResult(
        ticket_id=updated_ticket["id"],
        approval_status=(
            updated_ticket["approval_status"]
        ),
        status=updated_ticket["status"],
        approved_by=updated_ticket.get(
            "approved_by"
        ),
        approved_at=updated_ticket.get(
            "approved_at"
        ),
    )