from typing import Any
from datetime import datetime, timezone
from app.db.supabase import get_supabase_client
from app.tickets.schemas import TicketCreate


def get_ticket_by_idempotency_key(
    idempotency_key: str,
    user_id: str,
) -> dict[str, Any] | None:
    """
    Find an existing ticket by its idempotency key.

    Ownership is included in the query so one user cannot use an
    idempotency key to retrieve another user's ticket.
    """

    idempotency_key = idempotency_key.strip()

    if not idempotency_key:
        raise ValueError(
            "Idempotency key cannot be empty."
        )

    client = get_supabase_client()

    response = (
        client
        .table("support_tickets")
        .select("*")
        .eq(
            "idempotency_key",
            idempotency_key,
        )
        .eq(
            "user_id",
            user_id,
        )
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]


def create_ticket(
    ticket: TicketCreate,
) -> dict[str, Any]:
    """
    Persist a new internal Harbor support ticket.

    Ticket creation is idempotent. If the same user submits the same
    idempotency key again, Harbor returns the existing ticket instead
    of inserting a duplicate.

    This creates only Harbor's internal pending ticket. It does not
    perform any Monday.com, n8n, or other external side effect.
    """

    user_id = str(ticket.user_id)

    existing_ticket = (
        get_ticket_by_idempotency_key(
            idempotency_key=ticket.idempotency_key,
            user_id=user_id,
        )
    )

    if existing_ticket is not None:
        return existing_ticket

    client = get_supabase_client()

    payload = {
        "user_id": user_id,
        "conversation_id": str(
            ticket.conversation_id
        ),
        "title": ticket.title,
        "description": ticket.description,
        "severity": ticket.severity,
        "status": "pending_approval",
        "approval_status": "pending",
        "idempotency_key": (
            ticket.idempotency_key
        ),
    }

    response = (
        client
        .table("support_tickets")
        .insert(payload)
        .execute()
    )

    if not response.data:
        raise RuntimeError(
            "Failed to create support ticket."
        )

    return response.data[0]


def get_ticket(
    ticket_id: str,
    user_id: str,
) -> dict[str, Any] | None:
    """
    Fetch one ticket while enforcing ownership.

    Both the ticket ID and authenticated user ID are included in the
    query so users cannot access tickets owned by other users.
    """

    client = get_supabase_client()

    response = (
        client
        .table("support_tickets")
        .select("*")
        .eq(
            "id",
            ticket_id,
        )
        .eq(
            "user_id",
            user_id,
        )
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]


def list_tickets(
    user_id: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Return the authenticated user's most recently created tickets.
    """

    if limit <= 0:
        raise ValueError(
            "Ticket list limit must be greater than zero."
        )

    client = get_supabase_client()

    response = (
        client
        .table("support_tickets")
        .select("*")
        .eq(
            "user_id",
            user_id,
        )
        .order(
            "created_at",
            desc=True,
        )
        .limit(limit)
        .execute()
    )

    return response.data or []


def get_ticket_for_review(
    ticket_id: str,
) -> dict[str, Any] | None:
    """
    Fetch a ticket for an authorized human reviewer.

    Unlike get_ticket(), this function does not filter by the
    ticket owner's user ID because support agents and admins
    review tickets belonging to other users.

    Authorization must therefore be enforced by the service/API
    boundary before this repository operation is exposed.
    """

    client = get_supabase_client()

    response = (
        client
        .table("support_tickets")
        .select("*")
        .eq(
            "id",
            ticket_id,
        )
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]


def approve_ticket(
    ticket_id: str,
    approved_by: str,
) -> dict[str, Any] | None:
    """
    Atomically approve a currently pending Harbor ticket.

    The update is restricted to tickets whose workflow is
    still pending approval. If the ticket does not exist or
    has already been decided, no row is returned.

    Approval only changes Harbor's internal ticket state.
    It does not create an external Monday.com item or trigger
    any other side effect.
    """

    approved_at = datetime.now(
        timezone.utc
    ).isoformat()

    client = get_supabase_client()

    response = (
        client
        .table("support_tickets")
        .update(
            {
                "approval_status": "approved",
                "status": "approved",
                "approved_by": approved_by,
                "approved_at": approved_at,
                "updated_at": approved_at,
            }
        )
        .eq(
            "id",
            ticket_id,
        )
        .eq(
            "approval_status",
            "pending",
        )
        .eq(
            "status",
            "pending_approval",
        )
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]


def reject_ticket(
    ticket_id: str,
    rejected_by: str,
) -> dict[str, Any] | None:
    """
    Atomically reject a currently pending Harbor ticket.

    A rejected ticket cannot proceed to external execution.
    The reviewer is recorded in approved_by because the
    current database schema uses that column for the human
    decision actor.

    If the ticket does not exist or is no longer pending,
    no row is returned.
    """

    decided_at = datetime.now(
        timezone.utc
    ).isoformat()

    client = get_supabase_client()

    response = (
        client
        .table("support_tickets")
        .update(
            {
                "approval_status": "rejected",
                "status": "rejected",
                "approved_by": rejected_by,
                "approved_at": decided_at,
                "updated_at": decided_at,
            }
        )
        .eq(
            "id",
            ticket_id,
        )
        .eq(
            "approval_status",
            "pending",
        )
        .eq(
            "status",
            "pending_approval",
        )
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]