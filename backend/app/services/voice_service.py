import hashlib
import logging
from typing import Any
from uuid import UUID

from app.db.supabase import (
    get_supabase_client,
)

from app.repositories.conversations import (
    create_conversation,
)

from app.repositories.ticket_repository import (
    create_ticket,
)

from app.services.ticket_service import (
    prepare_ticket_content,
)

from app.tickets.schemas import (
    TicketCreate,
    TicketSeverity,
)


logger = logging.getLogger(
    "harbor.voice_service"
)


# ============================================================
# EXCEPTIONS
# ============================================================

class VoiceCustomerNotFoundError(
    Exception
):
    """
    Raised when the caller cannot be matched to an existing
    Harbor customer account.
    """


class VoiceTicketConfirmationRequiredError(
    Exception
):
    """
    Raised when Retell attempts to create a support ticket
    without explicit customer confirmation.
    """


class VoiceTicketCreationError(
    Exception
):
    """
    Raised when Harbor cannot safely create the voice ticket.
    """


# ============================================================
# CUSTOMER LOOKUP
# ============================================================

def get_customer_by_email(
    email: str,
) -> dict[str, Any] | None:
    """
    Find an existing Harbor customer by email.

    Voice calls currently use the customer's Harbor account
    email as the identity bridge between Retell and Harbor.
    """

    if not isinstance(
        email,
        str,
    ):
        raise TypeError(
            "Customer email must be a string."
        )

    email = (
        email
        .strip()
        .lower()
    )

    if not email:
        raise ValueError(
            "Customer email cannot be empty."
        )

    client = (
        get_supabase_client()
    )

    response = (
        client
        .table(
            "users"
        )
        .select(
            (
                "id,"
                "email,"
                "full_name,"
                "role,"
                "is_active"
            )
        )
        .eq(
            "email",
            email,
        )
        .limit(
            1
        )
        .execute()
    )

    if not response.data:
        return None

    customer = (
        response.data[0]
    )

    # Only normal Harbor customers should create customer
    # support tickets through the voice interface.
    if (
        customer.get(
            "role"
        )
        != "customer"
    ):
        return None

    if (
        customer.get(
            "is_active"
        )
        is False
    ):
        return None

    return customer


# ============================================================
# VOICE IDEMPOTENCY
# ============================================================

def build_voice_ticket_idempotency_key(
    *,
    user_id: str,
    call_id: str,
    description: str,
) -> str:
    """
    Build deterministic ticket identity for a Retell call.

    This prevents Retell retries from creating duplicate
    Harbor tickets.

    The call ID is important because the same customer may
    legitimately report the same issue in a future call.
    """

    user_id = (
        user_id.strip()
    )

    call_id = (
        call_id.strip()
    )

    description = (
        description.strip()
    )

    if not user_id:
        raise ValueError(
            "User ID cannot be empty."
        )

    if not call_id:
        raise ValueError(
            "Voice call ID cannot be empty."
        )

    if not description:
        raise ValueError(
            "Ticket description cannot be empty."
        )

    normalized = "|".join(
        [
            "retell",
            user_id,
            call_id,
            description,
        ]
    )

    digest = (
        hashlib.sha256(
            normalized.encode(
                "utf-8"
            )
        )
        .hexdigest()
    )

    return (
        f"harbor-voice-{digest}"
    )


def get_existing_voice_ticket(
    *,
    user_id: str,
    idempotency_key: str,
) -> dict[str, Any] | None:
    """
    Check for an already-created ticket before creating a
    conversation.

    Doing this first avoids creating orphaned conversations
    when Retell retries the same function call.
    """

    client = (
        get_supabase_client()
    )

    response = (
        client
        .table(
            "support_tickets"
        )
        .select(
            "*"
        )
        .eq(
            "user_id",
            user_id,
        )
        .eq(
            "idempotency_key",
            idempotency_key,
        )
        .limit(
            1
        )
        .execute()
    )

    if not response.data:
        return None

    return (
        response.data[0]
    )


# ============================================================
# TITLE
# ============================================================

def build_voice_ticket_title(
    issue: str,
) -> str:
    """
    Build a short ticket title from the caller's issue.

    No LLM call is needed here because this is only an
    internal support-ticket title.
    """

    cleaned = " ".join(
        issue
        .strip()
        .split()
    )

    if not cleaned:
        return (
            "Voice Support Request"
        )

    max_length = 100

    if len(
        cleaned
    ) <= max_length:
        return cleaned

    return (
        cleaned[
            : max_length - 3
        ].rstrip()
        + "..."
    )


# ============================================================
# CREATE VOICE SUPPORT TICKET
# ============================================================

def create_voice_support_ticket(
    *,
    customer_email: str,
    issue: str,
    call_id: str,
    confirmed: bool,
    severity: TicketSeverity = "medium",
) -> dict[str, Any]:
    """
    Create a customer-confirmed Harbor support ticket from a
    Retell voice call.

    Security boundaries:

    - caller must map to an existing Harbor customer;
    - customer must explicitly confirm ticket creation;
    - Harbor input guardrails sanitize ticket content;
    - ticket starts as pending_approval;
    - this function does NOT approve the ticket;
    - this function does NOT execute the ticket;
    - this function does NOT call Monday.com;
    - this function does NOT call n8n.

    Human approval remains mandatory.
    """

    # --------------------------------------------------------
    # 1. Explicit customer confirmation
    # --------------------------------------------------------

    if confirmed is not True:
        raise (
            VoiceTicketConfirmationRequiredError(
                (
                    "Explicit customer confirmation "
                    "is required before creating a "
                    "support ticket."
                )
            )
        )


    # --------------------------------------------------------
    # 2. Validate issue
    # --------------------------------------------------------

    if not isinstance(
        issue,
        str,
    ):
        raise TypeError(
            "Issue must be a string."
        )

    issue = (
        issue.strip()
    )

    if not issue:
        raise ValueError(
            "Issue cannot be empty."
        )


    # --------------------------------------------------------
    # 3. Validate call ID
    # --------------------------------------------------------

    if not isinstance(
        call_id,
        str,
    ):
        raise TypeError(
            "Voice call ID must be a string."
        )

    call_id = (
        call_id.strip()
    )

    if not call_id:
        raise ValueError(
            "Voice call ID cannot be empty."
        )


    # --------------------------------------------------------
    # 4. Validate severity
    # --------------------------------------------------------

    allowed_severities = {
        "low",
        "medium",
        "high",
        "critical",
    }

    if (
        severity
        not in allowed_severities
    ):
        severity = "medium"


    # --------------------------------------------------------
    # 5. Resolve Harbor customer
    # --------------------------------------------------------

    customer = (
        get_customer_by_email(
            customer_email
        )
    )

    if customer is None:
        raise (
            VoiceCustomerNotFoundError(
                (
                    "No active Harbor customer "
                    "account was found for that "
                    "email address."
                )
            )
        )

    user_id = str(
        customer[
            "id"
        ]
    )


    # --------------------------------------------------------
    # 6. Safe content
    # --------------------------------------------------------

    safe_description = (
        prepare_ticket_content(
            issue
        )
    )

    safe_title = (
        prepare_ticket_content(
            build_voice_ticket_title(
                safe_description
            )
        )
    )


    # --------------------------------------------------------
    # 7. Idempotency
    # --------------------------------------------------------

    idempotency_key = (
        build_voice_ticket_idempotency_key(
            user_id=user_id,
            call_id=call_id,
            description=(
                safe_description
            ),
        )
    )

    existing_ticket = (
        get_existing_voice_ticket(
            user_id=user_id,
            idempotency_key=(
                idempotency_key
            ),
        )
    )

    if (
        existing_ticket
        is not None
    ):
        logger.info(
            (
                "Returning existing Retell "
                "voice ticket | "
                "ticket_id=%s | "
                "call_id=%s"
            ),
            existing_ticket.get(
                "id"
            ),
            call_id,
        )

        return existing_ticket


    # --------------------------------------------------------
    # 8. Create Harbor conversation
    # --------------------------------------------------------

    conversation = (
        create_conversation(
            user_id=user_id,
            title=(
                "Voice Support Request"
            ),
        )
    )

    conversation_id = str(
        conversation[
            "id"
        ]
    )


    # --------------------------------------------------------
    # 9. Build normal Harbor ticket
    # --------------------------------------------------------

    try:
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

        created_ticket = (
            create_ticket(
                ticket
            )
        )

    except Exception as exc:
        logger.exception(
            (
                "Retell voice ticket creation "
                "failed | call_id=%s"
            ),
            call_id,
        )

        raise VoiceTicketCreationError(
            (
                "Harbor could not create the "
                "voice support ticket."
            )
        ) from exc


    logger.info(
        (
            "Retell voice ticket created | "
            "ticket_id=%s | "
            "user_id=%s | "
            "conversation_id=%s | "
            "call_id=%s"
        ),
        created_ticket.get(
            "id"
        ),
        user_id,
        conversation_id,
        call_id,
    )


    return created_ticket