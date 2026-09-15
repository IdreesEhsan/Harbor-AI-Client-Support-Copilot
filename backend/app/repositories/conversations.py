from typing import Any

from app.db.supabase import get_supabase_client


def create_conversation(
    user_id: str,
    title: str | None = None,
) -> dict[str, Any]:
    """
    Create a new conversation owned by the authenticated user.
    """

    client = get_supabase_client()

    payload = {
        "user_id": user_id,
        "title": title,
    }

    response = (
        client
        .table("conversations")
        .insert(payload)
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
    Fetch one conversation while enforcing ownership.

    Filtering by both conversation ID and user ID prevents one user
    from reading another user's conversation.
    """

    client = get_supabase_client()

    response = (
        client
        .table("conversations")
        .select("*")
        .eq("id", conversation_id)
        .eq("user_id", user_id)
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
    Return the authenticated user's most recently updated conversations.
    """

    client = get_supabase_client()

    response = (
        client
        .table("conversations")
        .select("*")
        .eq("user_id", user_id)
        .order(
            "updated_at",
            desc=True,
        )
        .limit(limit)
        .execute()
    )

    return response.data or []

def save_message(
    conversation_id: str,
    role: str,
    content: str,
) -> dict[str, Any]:
    """
    Persist one user, assistant, or system message.
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
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
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
    Load the most recent conversation messages in chronological order.

    The database query fetches newest first for efficiency, then the
    result is reversed so the model receives natural conversation order.
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
    Return the complete persistent conversation history.
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

def get_conversation_summary(
    conversation_id: str,
) -> dict[str, Any] | None:
    """
    Load the current compressed summary for a conversation.
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
    Create or replace the conversation's current summary.
    """

    client = get_supabase_client()

    payload = {
        "conversation_id": conversation_id,
        "summary": summary,
        "summarized_until": summarized_until,
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

def touch_conversation(
    conversation_id: str,
) -> None:
    """
    Update conversation activity time after a new message is stored.
    """

    from datetime import datetime, timezone

    client = get_supabase_client()

    (
        client
        .table("conversations")
        .update(
            {
                "updated_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                )
            }
        )
        .eq(
            "id",
            conversation_id,
        )
        .execute()
    )