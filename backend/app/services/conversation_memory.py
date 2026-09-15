from typing import Any

from app.core.config import get_settings
from app.repositories.conversations import (
    get_all_messages,
    get_conversation_summary,
    upsert_conversation_summary,
)
from app.services.memory_service import (
    format_history,
    get_unsummarized_messages,
    summarize_conversation,
)


def update_summary_memory(
    conversation_id: str,
) -> str | None:
    """
    Update Harbor's persistent summary memory when a conversation
    has grown beyond the configured threshold.
    """

    settings = get_settings()

    messages = get_all_messages(
        conversation_id
    )

    if (
        len(messages)
        <= settings.memory_summary_threshold
    ):
        existing = get_conversation_summary(
            conversation_id
        )

        if existing:
            return existing.get(
                "summary"
            )

        return None

    existing_record = (
        get_conversation_summary(
            conversation_id
        )
    )

    existing_summary = None
    summarized_until = None

    if existing_record:
        existing_summary = (
            existing_record.get(
                "summary"
            )
        )

        summarized_until = (
            existing_record.get(
                "summarized_until"
            )
        )

    candidates = get_unsummarized_messages(
        messages=messages,
        summarized_until=summarized_until,
        buffer_size=settings.memory_buffer_size,
    )

    if not candidates:
        return existing_summary

    formatted_candidates = format_history(
        candidates
    )

    if not formatted_candidates:
        return existing_summary

    updated_summary = summarize_conversation(
        messages=formatted_candidates,
        existing_summary=existing_summary,
    )

    last_summarized_message = (
        candidates[-1]
    )

    new_summarized_until = (
        last_summarized_message.get(
            "created_at"
        )
    )

    if not new_summarized_until:
        raise RuntimeError(
            "Cannot persist summary without a message timestamp."
        )

    upsert_conversation_summary(
        conversation_id=conversation_id,
        summary=updated_summary,
        summarized_until=new_summarized_until,
    )

    return updated_summary