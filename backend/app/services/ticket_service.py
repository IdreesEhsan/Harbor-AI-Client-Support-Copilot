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

    Ticket records must never become a bypass around the
    normal input guardrails.
    """


class TicketNotFoundError(Exception):
    """
    Raised when a support ticket cannot be found for review.
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

    Safe content is preserved. PII and credentials are
    replaced with their guardrail-safe representations.

    Content classified as blocked is rejected completely
    instead of being written into the ticket record.
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

    # Fail closed if the guardrail contract changes in the
    # future and an unknown status reaches this boundary.
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

    Raw customer content is not stored inside the key.
    Instead, Harbor hashes the identifying ticket fields.

    Retrying the same logical escalation therefore produces
    the same key and prevents duplicate ticket creation.
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

    The operation:

    1. verifies conversation ownership;
    2. sanitizes ticket content;
    3. creates a deterministic idempotency key;
    4. creates a pending internal ticket.

    This does not approve the ticket and does not execute
    Monday.com, n8n, notification, or other external actions.
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
    Return one ticket owned by the authenticated user.
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
    Return tickets belonging to the authenticated user.
    """

    return list_tickets(
        user_id=user_id,
        limit=limit,
    )


def review_ticket(
    *,
    ticket_id: str,
) -> dict[str, Any]:
    """
    Load a ticket for an authorized human reviewer.

    Role authorization is enforced by the API boundary.
    This service is responsible for validating that the
    requested ticket exists.
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

    This operation changes Harbor's internal ticket state
    only. It does not execute an external side effect such as
    creating a Monday.com item.

    The repository performs an additional conditional update
    so concurrent approval attempts cannot overwrite an
    already completed decision.
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

    # A second reviewer may have decided the ticket between
    # our initial read and the conditional database update.
    #
    # In that case the repository returns None rather than
    # overwriting the first reviewer's decision.
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