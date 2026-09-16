from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.db.supabase import get_supabase_client
from app.tickets.schemas import TicketCreate


def get_ticket_by_idempotency_key(
    idempotency_key: str,
    user_id: str,
) -> dict[str, Any] | None:
    """
    Find an existing ticket by its idempotency key.

    Ownership is included in the query so one user cannot use
    an idempotency key to retrieve another user's ticket.
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

    Ticket creation is idempotent. If the same user submits
    the same idempotency key again, Harbor returns the
    existing ticket instead of inserting a duplicate.

    This creates only Harbor's internal pending ticket. It
    does not perform any Monday.com, n8n, or other external
    side effect.
    """

    user_id = str(ticket.user_id)

    existing_ticket = (
        get_ticket_by_idempotency_key(
            idempotency_key=(
                ticket.idempotency_key
            ),
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

    Both the ticket ID and authenticated user ID are included
    in the query so users cannot access tickets owned by
    other users.
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
    Return the authenticated user's most recently created
    tickets.
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

    Authorization must therefore be enforced by the
    service/API boundary before this repository operation is
    exposed.
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

    Approval only changes Harbor's internal ticket state. It
    does not create an external Monday.com item or trigger
    another external side effect.
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


def mark_ticket_executed(
    ticket_id: str,
    monday_item_id: str,
    execution_claim_id: str,
) -> dict[str, Any] | None:
    """
    Record successful Monday.com synchronization for the
    worker that currently owns Harbor's execution claim.

    The update succeeds only when:
    - human approval remains approved;
    - workflow status is executing;
    - the persisted execution claim matches this worker;
    - no Monday item has already been recorded.

    Requiring the execution claim ID prevents an old or stale
    worker from finalizing execution after ownership has
    changed.

    Successful finalization transitions:

        executing -> open

    The temporary execution lease metadata is cleared after
    successful synchronization.

    This repository function does not call Monday.com.
    """

    if not isinstance(
        ticket_id,
        str,
    ):
        raise TypeError(
            "ticket_id must be a string."
        )

    if not isinstance(
        monday_item_id,
        str,
    ):
        raise TypeError(
            "monday_item_id must be a string."
        )

    if not isinstance(
        execution_claim_id,
        str,
    ):
        raise TypeError(
            "execution_claim_id must be a string."
        )

    ticket_id = ticket_id.strip()
    monday_item_id = monday_item_id.strip()
    execution_claim_id = (
        execution_claim_id.strip()
    )

    if not ticket_id:
        raise ValueError(
            "ticket_id cannot be empty."
        )

    if not monday_item_id:
        raise ValueError(
            "monday_item_id cannot be empty."
        )

    if not execution_claim_id:
        raise ValueError(
            "execution_claim_id cannot be empty."
        )

    synced_at = datetime.now(
        timezone.utc
    ).isoformat()

    client = get_supabase_client()

    response = (
        client
        .table("support_tickets")
        .update(
            {
                "monday_item_id": (
                    monday_item_id
                ),
                "status": "open",
                "external_status": "Open",
                "last_synced_at": synced_at,
                "failure_reason": None,

                # Successful synchronization releases the
                # temporary execution lease.
                "execution_claim_id": None,
                "execution_started_at": None,

                "updated_at": synced_at,
            }
        )
        .eq(
            "id",
            ticket_id,
        )
        .eq(
            "approval_status",
            "approved",
        )
        .eq(
            "status",
            "executing",
        )
        .eq(
            "execution_claim_id",
            execution_claim_id,
        )
        .is_(
            "monday_item_id",
            "null",
        )
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]


def claim_ticket_for_execution(
    ticket_id: str,
) -> dict[str, Any] | None:
    """
    Atomically claim an approved Harbor ticket for external
    execution.

    Only a ticket whose persisted state is exactly:

        approval_status = approved
        status = approved
        monday_item_id IS NULL

    may transition to:

        status = executing
        execution_claim_id = <unique UUID>
        execution_started_at = <UTC timestamp>

    The execution claim UUID identifies the worker attempt
    that owns the temporary execution lease.

    Later finalization must present the same claim ID.

    The conditional database update remains Harbor's
    concurrency boundary. If multiple workers attempt to
    claim the same ticket, only one approved -> executing
    transition can succeed.

    Returning None means this worker did not obtain the
    execution claim.
    """

    if not isinstance(
        ticket_id,
        str,
    ):
        raise TypeError(
            "ticket_id must be a string."
        )

    ticket_id = ticket_id.strip()

    if not ticket_id:
        raise ValueError(
            "ticket_id cannot be empty."
        )

    claimed_at = datetime.now(
        timezone.utc
    ).isoformat()

    execution_claim_id = str(
        uuid4()
    )

    client = get_supabase_client()

    response = (
        client
        .table("support_tickets")
        .update(
            {
                "status": "executing",
                "execution_claim_id": (
                    execution_claim_id
                ),
                "execution_started_at": (
                    claimed_at
                ),
                "updated_at": claimed_at,
            }
        )
        .eq(
            "id",
            ticket_id,
        )
        .eq(
            "approval_status",
            "approved",
        )
        .eq(
            "status",
            "approved",
        )
        .is_(
            "monday_item_id",
            "null",
        )
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]

def recover_stale_execution_claim(
    ticket_id: str,
    previous_claim_id: str,
) -> dict[str, Any] | None:
    """
    Atomically replace a stale execution lease with a new
    execution lease.

    The caller must first determine that the previous lease
    is stale. This repository function is responsible only
    for the atomic ownership transition.

    Recovery is permitted only when the persisted ticket
    still has exactly the execution claim that the recovery
    worker inspected:

        approval_status = approved
        status = executing
        execution_claim_id = previous_claim_id
        monday_item_id IS NULL

    If another worker has already recovered or finalized the
    ticket, the previous claim ID will no longer match and
    this update returns no row.

    This provides compare-and-swap behavior:

        OLD stale claim
              ↓
        conditional update
              ↓
        NEW execution claim

    The ticket remains in ``executing`` throughout recovery.
    It is never reopened to ``approved``.

    This function does not determine whether a lease is stale
    and does not perform any Monday.com operation.
    """

    if not isinstance(
        ticket_id,
        str,
    ):
        raise TypeError(
            "ticket_id must be a string."
        )

    if not isinstance(
        previous_claim_id,
        str,
    ):
        raise TypeError(
            "previous_claim_id must be a string."
        )

    ticket_id = ticket_id.strip()
    previous_claim_id = (
        previous_claim_id.strip()
    )

    if not ticket_id:
        raise ValueError(
            "ticket_id cannot be empty."
        )

    if not previous_claim_id:
        raise ValueError(
            "previous_claim_id cannot be empty."
        )

    recovered_at = datetime.now(
        timezone.utc
    ).isoformat()

    new_claim_id = str(
        uuid4()
    )

    client = get_supabase_client()

    response = (
        client
        .table("support_tickets")
        .update(
            {
                # The ticket deliberately remains executing.
                "status": "executing",
                "execution_claim_id": (
                    new_claim_id
                ),
                "execution_started_at": (
                    recovered_at
                ),
                "updated_at": recovered_at,
            }
        )
        .eq(
            "id",
            ticket_id,
        )
        .eq(
            "approval_status",
            "approved",
        )
        .eq(
            "status",
            "executing",
        )
        .eq(
            "execution_claim_id",
            previous_claim_id,
        )
        .is_(
            "monday_item_id",
            "null",
        )
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]