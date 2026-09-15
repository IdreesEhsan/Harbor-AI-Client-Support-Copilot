from typing import Any

from app.guardrails.pipeline import run_input_guardrails
from app.repositories.conversations import (
    create_conversation,
    get_conversation,
    get_conversation_summary,
    get_recent_messages,
    save_message,
    touch_conversation,
)


class ConversationNotFoundError(Exception):
    """
    Raised when a conversation does not exist or does not
    belong to the authenticated user.
    """


class UnsafeMessagePersistenceError(Exception):
    """
    Raised when Harbor refuses to persist user content that
    has been blocked by the input guardrail.

    Raw blocked content must never be written into normal
    conversation history.
    """


def prepare_conversation(
    user_id: str,
    conversation_id: str | None = None,
) -> dict[str, Any]:
    """
    Create a new conversation or validate ownership of an
    existing one.

    Ownership validation is intentionally performed before
    any messages are written to the conversation.
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


def prepare_user_message_for_persistence(
    message: str,
) -> str | None:
    """
    Apply Harbor's input guardrails before a user message is
    written to persistent conversation history.

    Persistence policy:

    - allow:
      Store the original message.

    - redact:
      Store only the sanitized version.

    - block:
      Do not store the user message.

    - escalate:
      Store sanitized content when available, otherwise the
      original content. This allows legitimate support issues
      requiring human review to remain available.

    Returning None means the message must not be persisted.
    """

    result = run_input_guardrails(
        message
    )

    if result.status == "allow":
        return message

    if result.status == "redact":
        return result.redacted_content

    if result.status == "block":
        return None

    if result.status == "escalate":
        return (
            result.redacted_content
            or message
        )

    # GuardrailStatus is currently constrained by Pydantic,
    # but failing closed here protects this boundary if the
    # contract changes later.
    return None


def save_user_message(
    conversation_id: str,
    message: str,
) -> dict[str, Any] | None:
    """
    Safely persist an authenticated user's message.

    Raw input is never written directly to conversation
    history. Harbor evaluates it first so PII/credentials can
    be sanitized and blocked content can be discarded.
    """

    safe_message = (
        prepare_user_message_for_persistence(
            message
        )
    )

    if safe_message is None:
        return None

    return save_message(
        conversation_id=conversation_id,
        role="user",
        content=safe_message,
    )


def save_assistant_message(
    conversation_id: str,
    message: str,
) -> dict[str, Any]:
    """
    Persist Harbor's final response in conversation history.

    Assistant output guardrails will be added separately in
    Phase 9 before this becomes the final output boundary.
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

    Only recent messages are returned so the LLM does not
    receive the complete conversation on every request.
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
    Store Harbor's response and mark the conversation as
    recently active.
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