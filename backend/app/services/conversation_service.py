from typing import Any

from app.repositories.conversations import (
    create_conversation,
    get_conversation,
    get_recent_messages,
    save_message,
    touch_conversation,
    get_conversation_summary,
)


class ConversationNotFoundError(Exception):
    """
    Raised when a conversation does not exist or does not belong
    to the authenticated user.
    """


def prepare_conversation(
    user_id: str,
    conversation_id: str | None = None,
) -> dict[str, Any]:
    """
    Create a new conversation or validate ownership of an existing one.

    Ownership validation is intentionally performed before any messages
    are written to the conversation.
    """

    if not conversation_id:
        return create_conversation(
            user_id=user_id,
        )

    conversation = get_conversation(
        conversation_id=conversation_id,
        user_id=user_id,
    )

    if conversation is None:
        raise ConversationNotFoundError(
            "Conversation was not found."
        )

    return conversation

def save_user_message(
    conversation_id: str,
    message: str,
) -> dict[str, Any]:
    """
    Persist the authenticated user's message before agent execution.
    """

    return save_message(
        conversation_id=conversation_id,
        role="user",
        content=message,
    )

def save_assistant_message(
    conversation_id: str,
    message: str,
) -> dict[str, Any]:
    """
    Persist Harbor's final response in conversation history.
    """

    return save_message(
        conversation_id=conversation_id,
        role="assistant",
        content=message,
    )

def load_recent_history(
    conversation_id: str,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """
    Load Harbor's short-term conversation buffer.

    Only recent messages are returned so the LLM does not receive the
    complete conversation on every request.
    """

    return get_recent_messages(
        conversation_id=conversation_id,
        limit=limit,
    )

def finalize_conversation_turn(
    conversation_id: str,
    assistant_message: str,
) -> None:
    """
    Store Harbor's response and mark the conversation as recently active.
    """

    save_assistant_message(
        conversation_id=conversation_id,
        message=assistant_message,
    )

    touch_conversation(
        conversation_id=conversation_id,
    )

def load_conversation_summary(
    conversation_id: str,
) -> str | None:
    """
    Load Harbor's persisted long-term conversation summary.
    """

    record = get_conversation_summary(
        conversation_id
    )

    if not record:
        return None

    summary = record.get(
        "summary"
    )

    if not summary:
        return None

    return str(summary).strip() or None