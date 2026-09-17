from datetime import (
    datetime,
    timezone,
)
from typing import Any

from app.db.supabase import (
    get_supabase_client,
)


# ============================================================
# CONVERSATIONS
# ============================================================

def create_conversation(
    user_id: str,
    title: str | None = None,
) -> dict[str, Any]:
    """
    Create a new AI conversation owned by one authenticated
    Harbor user.
    """

    client = get_supabase_client()

    response = (
        client
        .table("conversations")
        .insert(
            {
                "user_id": user_id,
                "title": title,
            }
        )
        .execute()
    )

    if not response.data:
        raise RuntimeError(
            "Failed to create conversation."
        )

    return response.data[0]


def get_conversation(
    conversation_id: str,
    user_id: str,
) -> dict[str, Any] | None:
    """
    Load a conversation while enforcing ownership.

    Both conversation ID and user ID are included in the
    database query so another customer cannot read the
    conversation.
    """

    client = get_supabase_client()

    response = (
        client
        .table("conversations")
        .select("*")
        .eq(
            "id",
            conversation_id,
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


def list_conversations(
    user_id: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Return the customer's most recently active conversations.
    """

    if limit <= 0:
        raise ValueError(
            "Conversation limit must be greater than zero."
        )

    client = get_supabase_client()

    response = (
        client
        .table("conversations")
        .select("*")
        .eq(
            "user_id",
            user_id,
        )
        .order(
            "updated_at",
            desc=True,
        )
        .limit(limit)
        .execute()
    )

    return response.data or []


def update_conversation_title(
    conversation_id: str,
    title: str,
) -> dict[str, Any] | None:
    """
    Set the generated conversation title once.

    Once a conversation has a title, later messages do not
    rename it.
    """

    title = title.strip()

    if not title:
        raise ValueError(
            "Conversation title cannot be empty."
        )

    client = get_supabase_client()

    response = (
        client
        .table("conversations")
        .update(
            {
                "title": title,
            }
        )
        .eq(
            "id",
            conversation_id,
        )
        .is_(
            "title",
            "null",
        )
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]


# ============================================================
# MESSAGES
# ============================================================

def save_message(
    conversation_id: str,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Persist one AI conversation message.

    Assistant metadata contains information required for the
    frontend to reconstruct the full old response:

    - citations
    - action
    - severity
    - escalation state
    - ticket ID
    - ticket status
    - approval status
    """

    content = content.strip()

    if not content:
        raise ValueError(
            "Message content cannot be empty."
        )

    if role not in {
        "user",
        "assistant",
        "system",
    }:
        raise ValueError(
            f"Unsupported message role: {role}"
        )

    client = get_supabase_client()

    payload = {
        "conversation_id":
            conversation_id,

        "role":
            role,

        "content":
            content,

        "metadata":
            metadata or {},
    }

    response = (
        client
        .table("messages")
        .insert(payload)
        .execute()
    )

    if not response.data:
        raise RuntimeError(
            "Failed to save message."
        )

    return response.data[0]


def get_recent_messages(
    conversation_id: str,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """
    Return recent messages in chronological order.
    """

    client = get_supabase_client()

    response = (
        client
        .table("messages")
        .select("*")
        .eq(
            "conversation_id",
            conversation_id,
        )
        .order(
            "created_at",
            desc=True,
        )
        .limit(limit)
        .execute()
    )

    rows = response.data or []

    return list(
        reversed(rows)
    )


def get_all_messages(
    conversation_id: str,
) -> list[dict[str, Any]]:
    """
    Return all persisted messages for one conversation.
    """

    client = get_supabase_client()

    response = (
        client
        .table("messages")
        .select("*")
        .eq(
            "conversation_id",
            conversation_id,
        )
        .order(
            "created_at",
        )
        .execute()
    )

    return response.data or []


def get_first_user_message(
    conversation_id: str,
) -> dict[str, Any] | None:
    """
    Load only the first customer message.

    This is used when Harbor creates the short AI-generated
    sidebar title.
    """

    client = get_supabase_client()

    response = (
        client
        .table("messages")
        .select("*")
        .eq(
            "conversation_id",
            conversation_id,
        )
        .eq(
            "role",
            "user",
        )
        .order(
            "created_at",
        )
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]


def get_messages_for_conversations(
    conversation_ids: list[str],
) -> list[dict[str, Any]]:
    """
    Load messages for many sidebar conversations in one
    database request.

    This removes the previous N+1 query pattern.
    """

    cleaned_ids = [
        str(item).strip()
        for item in conversation_ids
        if str(item).strip()
    ]

    if not cleaned_ids:
        return []

    client = get_supabase_client()

    response = (
        client
        .table("messages")
        .select(
            (
                "id,"
                "conversation_id,"
                "role,"
                "content,"
                "metadata,"
                "created_at"
            )
        )
        .in_(
            "conversation_id",
            cleaned_ids,
        )
        .order(
            "created_at",
        )
        .execute()
    )

    return response.data or []


# ============================================================
# CONVERSATION SUMMARY MEMORY
# ============================================================

def get_conversation_summary(
    conversation_id: str,
) -> dict[str, Any] | None:
    """
    Load Harbor's compressed long-term conversation memory.
    """

    client = get_supabase_client()

    response = (
        client
        .table("conversation_summaries")
        .select("*")
        .eq(
            "conversation_id",
            conversation_id,
        )
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]


def upsert_conversation_summary(
    conversation_id: str,
    summary: str,
    summarized_until: str | None,
) -> dict[str, Any]:
    """
    Create or update the persistent conversation summary.
    """

    client = get_supabase_client()

    payload = {
        "conversation_id":
            conversation_id,

        "summary":
            summary,

        "summarized_until":
            summarized_until,
    }

    response = (
        client
        .table("conversation_summaries")
        .upsert(
            payload,
            on_conflict="conversation_id",
        )
        .execute()
    )

    if not response.data:
        raise RuntimeError(
            "Failed to save conversation summary."
        )

    return response.data[0]


# ============================================================
# ACTIVITY
# ============================================================

def touch_conversation(
    conversation_id: str,
) -> None:
    """
    Move the conversation to the top of the sidebar when a
    new turn is completed.
    """

    client = get_supabase_client()

    (
        client
        .table("conversations")
        .update(
            {
                "updated_at":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),
            }
        )
        .eq(
            "id",
            conversation_id,
        )
        .execute()
    )