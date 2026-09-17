import logging
import threading
from collections import defaultdict
from typing import Any

from app.core.config import (
    get_settings,
)

from app.guardrails.pipeline import (
    run_input_guardrails,
)

from app.rag.generator import (
    get_groq_client,
)

from app.repositories.conversations import (
    create_conversation,
    get_all_messages,
    get_conversation,
    get_conversation_summary,
    get_first_user_message,
    get_messages_for_conversations,
    get_recent_messages,
    list_conversations,
    save_message,
    touch_conversation,
    update_conversation_title,
)


settings = get_settings()

logger = logging.getLogger(
    "harbor.conversations"
)


class ConversationNotFoundError(
    Exception
):
    """
    Conversation does not exist or does not belong to the
    authenticated user.
    """


class UnsafeMessagePersistenceError(
    Exception
):
    """
    Harbor refused to persist blocked customer content.
    """


# ============================================================
# CONVERSATION CREATION / OWNERSHIP
# ============================================================

def prepare_conversation(
    user_id: str,
    conversation_id: str | None = None,
) -> dict[str, Any]:
    """
    Create a new conversation or validate ownership of an
    existing one.
    """

    if not conversation_id:
        return create_conversation(
            user_id=user_id,
        )

    conversation = (
        get_conversation(
            conversation_id=(
                conversation_id
            ),
            user_id=user_id,
        )
    )

    if conversation is None:
        raise ConversationNotFoundError(
            "Conversation was not found."
        )

    return conversation


# ============================================================
# SAFE USER MESSAGE PERSISTENCE
# ============================================================

def prepare_user_message_for_persistence(
    message: str,
) -> str | None:
    """
    Run the input guardrail before persistent storage.

    Raw blocked content is never stored in normal history.
    """

    result = (
        run_input_guardrails(
            message
        )
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

    return None


def save_user_message(
    conversation_id: str,
    message: str,
) -> dict[str, Any] | None:
    """
    Safely persist a customer message.
    """

    safe_message = (
        prepare_user_message_for_persistence(
            message
        )
    )

    if safe_message is None:
        return None

    return save_message(
        conversation_id=(
            conversation_id
        ),
        role="user",
        content=safe_message,
        metadata={},
    )


# ============================================================
# ASSISTANT MESSAGE PERSISTENCE
# ============================================================

def save_assistant_message(
    conversation_id: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Persist the final Harbor answer plus metadata needed to
    rebuild the UI later.
    """

    return save_message(
        conversation_id=(
            conversation_id
        ),
        role="assistant",
        content=message,
        metadata=(
            metadata or {}
        ),
    )


# ============================================================
# TITLE GENERATION
# ============================================================

def generate_conversation_title(
    first_message: str,
) -> str:
    """
    Generate a real semantic summary title from the first
    customer message.

    Expected output:
        Duplicate Charge Refund
        Account Login Problem
        Subscription Refund Policy

    The title is intentionally short so it fits naturally in
    the left sidebar.
    """

    first_message = (
        first_message.strip()
    )

    if not first_message:
        return "Support Request"

    system_prompt = """
You create short titles for customer-support conversations.

Summarize the main topic or problem from the customer's first message.

Rules:
- Use 3 to 6 words.
- Summarize the meaning, not the exact wording.
- Do not copy the entire customer message.
- Do not use quotation marks.
- Do not end with punctuation.
- Do not use the words Customer, User, Harbor, Chat, or Conversation.
- Return only the title.

Examples:

"I was charged twice and need one payment refunded."
Duplicate Charge Refund

"I cannot log into my account after resetting my password."
Account Login Problem

"What is your refund policy for cancelled subscriptions?"
Subscription Refund Policy
""".strip()

    client = (
        get_groq_client()
    )

    response = (
        client
        .chat
        .completions
        .create(
            model=(
                settings.groq_model
            ),
            messages=[
                {
                    "role":
                        "system",

                    "content":
                        system_prompt,
                },
                {
                    "role":
                        "user",

                    "content":
                        first_message,
                },
            ],
            temperature=0.0,
        )
    )

    title = (
        response
        .choices[0]
        .message
        .content
        or ""
    ).strip()

    title = (
        title
        .strip("\"' ")
        .rstrip(".!?")
        .strip()
    )

    if not title:
        return "Support Request"

    words = title.split()

    if len(words) > 6:
        title = " ".join(
            words[:6]
        )

    if len(title) > 80:
        title = (
            title[:77]
            .rstrip()
            + "..."
        )

    return title


def ensure_conversation_title(
    conversation_id: str,
) -> None:
    """
    Generate a title only if the conversation does not
    already have one.

    Failures are intentionally isolated from the active
    support conversation.
    """

    try:
        first_message = (
            get_first_user_message(
                conversation_id
            )
        )

        if not first_message:
            return

        content = str(
            first_message.get(
                "content",
                "",
            )
        ).strip()

        if not content:
            return

        title = (
            generate_conversation_title(
                content
            )
        )

        update_conversation_title(
            conversation_id=(
                conversation_id
            ),
            title=title,
        )

    except Exception:
        logger.exception(
            (
                "Unable to generate conversation title | "
                "conversation_id=%s"
            ),
            conversation_id,
        )


def generate_title_in_background(
    conversation_id: str,
) -> None:
    """
    Generate the sidebar title outside the main AI response
    flow.

    This prevents title generation from increasing the time
    before Harbor's response is returned.
    """

    worker = threading.Thread(
        target=(
            ensure_conversation_title
        ),
        args=(
            conversation_id,
        ),
        daemon=True,
    )

    worker.start()


# ============================================================
# RECENT MEMORY
# ============================================================

def load_recent_history(
    conversation_id: str,
    limit: int = 8,
) -> list[dict[str, Any]]:
    return get_recent_messages(
        conversation_id=(
            conversation_id
        ),
        limit=limit,
    )


# ============================================================
# SUMMARY MEMORY
# ============================================================

def load_conversation_summary(
    conversation_id: str,
) -> str | None:
    record = (
        get_conversation_summary(
            conversation_id
        )
    )

    if not record:
        return None

    summary = (
        record.get(
            "summary"
        )
    )

    if not summary:
        return None

    return (
        str(summary).strip()
        or None
    )


# ============================================================
# FINALIZE TURN
# ============================================================

def finalize_conversation_turn(
    conversation_id: str,
    assistant_message: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """
    Persist the final assistant response and make the
    conversation recently active.
    """

    save_assistant_message(
        conversation_id=(
            conversation_id
        ),
        message=(
            assistant_message
        ),
        metadata=(
            metadata or {}
        ),
    )

    touch_conversation(
        conversation_id=(
            conversation_id
        )
    )

    generate_title_in_background(
        conversation_id
    )


# ============================================================
# SIDEBAR LIST
# ============================================================

def list_user_conversations(
    *,
    user_id: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Return the data required by the ChatGPT-style sidebar.

    Only two database requests are used:

        conversations
        messages for those conversations

    This avoids issuing separate first-message and
    latest-message queries for every conversation.
    """

    conversations = (
        list_conversations(
            user_id=user_id,
            limit=limit,
        )
    )

    if not conversations:
        return []

    conversation_ids = [
        str(
            conversation["id"]
        )
        for conversation
        in conversations
    ]

    messages = (
        get_messages_for_conversations(
            conversation_ids
        )
    )

    grouped_messages: dict[
        str,
        list[dict[str, Any]],
    ] = defaultdict(list)

    for message in messages:
        conversation_key = str(
            message.get(
                "conversation_id"
            )
        )

        grouped_messages[
            conversation_key
        ].append(
            message
        )

    result = []

    for conversation in conversations:
        record = dict(
            conversation
        )

        conversation_id = str(
            record["id"]
        )

        conversation_messages = (
            grouped_messages.get(
                conversation_id,
                [],
            )
        )

        title = (
            record.get(
                "title"
            )
        )

        if not title:
            title = (
                "New Support Conversation"
            )

        record[
            "title"
        ] = title

        preview = ""

        if conversation_messages:
            latest_message = (
                conversation_messages[-1]
            )

            preview = str(
                latest_message.get(
                    "content",
                    "",
                )
            ).strip()

        if len(preview) > 100:
            preview = (
                preview[:97]
                .rstrip()
                + "..."
            )

        record[
            "preview"
        ] = preview

        result.append(
            record
        )

    return result


# ============================================================
# OPEN OLD CONVERSATION
# ============================================================

def get_user_conversation_history(
    *,
    user_id: str,
    conversation_id: str,
) -> dict[str, Any]:
    """
    Return one owned conversation plus complete persisted
    message metadata.
    """

    conversation = (
        get_conversation(
            conversation_id=(
                conversation_id
            ),
            user_id=user_id,
        )
    )

    if conversation is None:
        raise ConversationNotFoundError(
            "Conversation was not found."
        )

    messages = (
        get_all_messages(
            conversation_id
        )
    )

    return {
        "conversation":
            conversation,

        "messages":
            messages,
    }