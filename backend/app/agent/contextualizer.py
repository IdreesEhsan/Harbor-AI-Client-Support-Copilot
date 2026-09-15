from app.core.config import get_settings
from app.core.prompts import load_prompt
from app.rag.generator import get_groq_client
from app.services.memory_service import (
    history_to_text,
)


def contextualize_question(
    question: str,
    history: list[dict[str, str]],
    conversation_summary: str | None = None,
) -> str:
    """
    Rewrite a contextual or follow-up customer-support message into
    a standalone retrieval query.

    Harbor uses:
    - conversation_summary as long-term conversational memory
    - history as recent short-term buffer memory

    These memory sources are used only to understand the current
    question. They are not treated as verified knowledge-base facts.
    """

    question = question.strip()

    if not question:
        raise ValueError(
            "Question cannot be empty."
        )

    # If Harbor has no previous conversational context, the current
    # question is already the only available retrieval query.
    # Avoiding an unnecessary Groq call also reduces latency and cost.
    if not history and not conversation_summary:
        return question

    settings = get_settings()

    system_prompt = load_prompt(
        "contextualize_question.txt"
    )

    # Convert recent user/assistant turns into a readable
    # representation for the contextualization prompt.
    history_text = history_to_text(
        history
    )

    # Long-term summary memory may not exist for short or
    # newly created conversations.
    summary_context = (
        conversation_summary.strip()
        if conversation_summary
        else "No previous conversation summary."
    )

    # Keep long-term memory, recent memory, and the current
    # message clearly separated in the prompt.
    user_prompt = f"""
CONVERSATION SUMMARY

{summary_context}

RECENT CONVERSATION

{history_text}

CURRENT MESSAGE

{question}
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

    rewritten = (
        response
        .choices[0]
        .message
        .content
        or ""
    ).strip()

    # If Groq unexpectedly returns an empty response, fall back to the
    # original question rather than breaking the RAG pipeline.
    return rewritten or question