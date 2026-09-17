from datetime import (
    datetime,
    timezone,
)
from typing import Any
from uuid import uuid4

from app.db.supabase import (
    get_supabase_client,
)
from app.tickets.schemas import (
    TicketCreate,
)


# ============================================================
# CUSTOMER PROFILE LOOKUP
# ============================================================

def get_customer_profile(
    user_id: str,
) -> dict[str, Any] | None:
    """
    Return the support-relevant profile fields for one
    Harbor customer.

    Password-related fields are deliberately not selected.
    """

    if not isinstance(
        user_id,
        str,
    ):
        raise TypeError(
            "user_id must be a string."
        )

    user_id = user_id.strip()

    if not user_id:
        raise ValueError(
            "user_id cannot be empty."
        )

    client = get_supabase_client()

    response = (
        client
        .table("users")
        .select(
            (
                "id,"
                "email,"
                "full_name,"
                "age,"
                "country"
            )
        )
        .eq(
            "id",
            user_id,
        )
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]


def get_customer_profiles(
    user_ids: list[str],
) -> dict[str, dict[str, Any]]:
    """
    Fetch customer profiles in one query.

    Returns:
        {
            "<user-id>": {
                ...
            }
        }

    This avoids issuing one database request per ticket.
    """

    cleaned_ids = list(
        {
            str(user_id).strip()
            for user_id
            in user_ids
            if str(user_id).strip()
        }
    )

    if not cleaned_ids:
        return {}

    client = get_supabase_client()

    response = (
        client
        .table("users")
        .select(
            (
                "id,"
                "email,"
                "full_name,"
                "age,"
                "country"
            )
        )
        .in_(
            "id",
            cleaned_ids,
        )
        .execute()
    )

    profiles = (
        response.data
        or []
    )

    return {
        str(profile["id"]):
            profile
        for profile
        in profiles
        if profile.get("id")
    }


# ============================================================
# IDEMPOTENCY
# ============================================================

def get_ticket_by_idempotency_key(
    idempotency_key: str,
    user_id: str,
) -> dict[str, Any] | None:
    """
    Find an existing ticket using the customer and
    deterministic idempotency key.
    """

    idempotency_key = (
        idempotency_key.strip()
    )

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


# ============================================================
# CREATE
# ============================================================

def create_ticket(
    ticket: TicketCreate,
) -> dict[str, Any]:
    """
    Persist Harbor's internal support ticket.

    New tickets begin in pending approval and do not
    trigger an external business action.
    """

    user_id = str(
        ticket.user_id
    )

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
        "user_id":
            user_id,

        "conversation_id":
            str(
                ticket.conversation_id
            ),

        "title":
            ticket.title,

        "description":
            ticket.description,

        "severity":
            ticket.severity,

        "status":
            "pending_approval",

        "approval_status":
            "pending",

        "idempotency_key":
            ticket.idempotency_key,
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


# ============================================================
# CUSTOMER-SCOPED TICKET QUERIES
# ============================================================

def get_ticket(
    ticket_id: str,
    user_id: str,
) -> dict[str, Any] | None:
    """
    Return one customer-owned ticket.

    Both identifiers are part of the query to enforce
    ownership.
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
    Return tickets belonging to one authenticated
    customer.

    This will later be used by My Cases.
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

    return (
        response.data
        or []
    )


# ============================================================
# STAFF TICKET QUERIES
# ============================================================

def list_all_tickets(
    limit: int = 100,
) -> list[dict[str, Any]]:
    """
    Return support tickets across all customers.

    This method is intentionally unscoped and must only
    be called behind staff RBAC.
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
        .order(
            "created_at",
            desc=True,
        )
        .limit(limit)
        .execute()
    )

    return (
        response.data
        or []
    )


def get_ticket_for_review(
    ticket_id: str,
) -> dict[str, Any] | None:
    """
    Return one ticket for an authorized Harbor support
    agent.

    This query is intentionally not ownership scoped.
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


# ============================================================
# APPROVAL
# ============================================================

def approve_ticket(
    ticket_id: str,
    approved_by: str,
) -> dict[str, Any] | None:
    """
    Approve an internal pending Harbor ticket.
    """

    approved_at = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    client = get_supabase_client()

    response = (
        client
        .table("support_tickets")
        .update(
            {
                "approval_status":
                    "approved",

                "status":
                    "approved",

                "approved_by":
                    approved_by,

                "approved_at":
                    approved_at,

                "updated_at":
                    approved_at,
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
    Reject a pending Harbor support ticket.
    """

    decided_at = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    client = get_supabase_client()

    response = (
        client
        .table("support_tickets")
        .update(
            {
                "approval_status":
                    "rejected",

                "status":
                    "rejected",

                "approved_by":
                    rejected_by,

                "approved_at":
                    decided_at,

                "updated_at":
                    decided_at,
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


# ============================================================
# EXECUTION CLAIM
# ============================================================

def claim_ticket_for_execution(
    ticket_id: str,
) -> dict[str, Any] | None:
    """
    Atomically claim an approved ticket before performing
    an external operation.
    """

    if not isinstance(
        ticket_id,
        str,
    ):
        raise TypeError(
            "ticket_id must be a string."
        )

    ticket_id = (
        ticket_id.strip()
    )

    if not ticket_id:
        raise ValueError(
            "ticket_id cannot be empty."
        )

    claimed_at = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    execution_claim_id = str(
        uuid4()
    )

    client = get_supabase_client()

    response = (
        client
        .table("support_tickets")
        .update(
            {
                "status":
                    "executing",

                "execution_claim_id":
                    execution_claim_id,

                "execution_started_at":
                    claimed_at,

                "updated_at":
                    claimed_at,
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
    Replace a stale execution claim using a conditional
    compare-and-swap style update.
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

    ticket_id = (
        ticket_id.strip()
    )

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

    recovered_at = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    new_claim_id = str(
        uuid4()
    )

    client = get_supabase_client()

    response = (
        client
        .table("support_tickets")
        .update(
            {
                "status":
                    "executing",

                "execution_claim_id":
                    new_claim_id,

                "execution_started_at":
                    recovered_at,

                "updated_at":
                    recovered_at,
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


# ============================================================
# EXECUTION FINALIZATION
# ============================================================

def mark_ticket_executed(
    ticket_id: str,
    monday_item_id: str,
    execution_claim_id: str,
) -> dict[str, Any] | None:
    """
    Persist successful Monday.com synchronization.
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

    ticket_id = (
        ticket_id.strip()
    )

    monday_item_id = (
        monday_item_id.strip()
    )

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

    synced_at = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    client = get_supabase_client()

    response = (
        client
        .table("support_tickets")
        .update(
            {
                "monday_item_id":
                    monday_item_id,

                "status":
                    "open",

                "external_status":
                    "Open",

                "last_synced_at":
                    synced_at,

                "failure_reason":
                    None,

                "execution_claim_id":
                    None,

                "execution_started_at":
                    None,

                "updated_at":
                    synced_at,
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