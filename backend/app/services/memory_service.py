from typing import Any
from app.core.config import get_settings
from app.core.prompts import load_prompt
from app.rag.generator import get_groq_client
from datetime import datetime

def format_history(
    messages: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """
    Convert persisted database messages into the minimal conversation
    format needed by Harbor's agent.

    Database-only metadata is intentionally excluded from LLM context.
    """

    history: list[dict[str, str]] = []

    for message in messages:
        role = message.get("role")
        content = str(
            message.get("content", "")
        ).strip()

        if role not in {
            "user",
            "assistant",
        }:
            continue

        if not content:
            continue

        history.append(
            {
                "role": role,
                "content": content,
            }
        )

    return history

def history_to_text(
    history: list[dict[str, str]],
) -> str:
    """
    Convert recent conversation turns into a readable prompt section.
    """

    if not history:
        return "No previous conversation."

    lines: list[str] = []

    for message in history:
        role = message["role"]
        content = message["content"]

        label = (
            "User"
            if role == "user"
            else "Assistant"
        )

        lines.append(
            f"{label}: {content}"
        )

    return "\n".join(lines)

def summarize_conversation(
    messages: list[dict[str, str]],
    existing_summary: str | None = None,
) -> str:
    """
    Use Groq to compress older conversation messages into
    persistent long-term memory.

    Existing summary memory is included so Harbor can update
    the summary incrementally instead of starting from scratch.
    """

    if not messages:
        return existing_summary or ""

    settings = get_settings()

    system_prompt = load_prompt(
        "summarize_conversation.txt"
    )

    history_text = history_to_text(
        messages
    )

    previous_summary = (
        existing_summary.strip()
        if existing_summary
        else "No existing summary."
    )

    user_prompt = f"""
EXISTING CONVERSATION SUMMARY

{previous_summary}

NEW CONVERSATION MESSAGES

{history_text}

Create the updated conversation summary.
""".strip()

    client = get_groq_client()

    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        temperature=0.0,
    )

    summary = (
        response
        .choices[0]
        .message
        .content
        or ""
    ).strip()

    if not summary:
        raise RuntimeError(
            "Groq returned an empty conversation summary."
        )

    return summary

def get_unsummarized_messages(
    messages: list[dict],
    summarized_until: str | None,
    buffer_size: int,
) -> list[dict]:
    """
    Return older messages that have not already been included
    in persistent summary memory.

    The newest buffer_size messages are always preserved as
    short-term memory instead of being summarized.
    """

    if len(messages) <= buffer_size:
        return []

    older_messages = messages[:-buffer_size]

    if not summarized_until:
        return older_messages

    cutoff = datetime.fromisoformat(
        summarized_until.replace(
            "Z",
            "+00:00",
        )
    )

    unsummarized = []

    for message in older_messages:
        created_at = message.get(
            "created_at"
        )

        if not created_at:
            continue

        message_time = datetime.fromisoformat(
            created_at.replace(
                "Z",
                "+00:00",
            )
        )

        if message_time > cutoff:
            unsummarized.append(
                message
            )

    return unsummarized