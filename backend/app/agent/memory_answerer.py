from app.core.config import get_settings
from app.core.prompts import load_prompt
from app.rag.generator import get_groq_client
from app.services.memory_service import history_to_text


settings = get_settings()


MEMORY_NO_ANSWER = (
    "I don't have that information in our "
    "conversation history."
)


class MemoryAnswerError(Exception):
    """
    Raised when Harbor cannot generate a valid
    conversation-memory answer.
    """


def answer_from_memory(
    question: str,
    history: list[dict[str, str]] | None = None,
    conversation_summary: str | None = None,
) -> str:
    """
    Answer a question using Harbor's conversation memory only.

    This function intentionally does not access the knowledge base.

    The conversation summary provides compressed long-term memory,
    while history provides the recent short-term buffer.

    User-provided conversational information is treated as contextual
    memory, not as verified Harbor policy or company records.
    """

    question = question.strip()

    if not question:
        raise ValueError(
            "Question cannot be empty."
        )

    history = history or []

    conversation_context = history_to_text(
        history
    )

    summary_context = (
        conversation_summary.strip()
        if conversation_summary
        else "No previous conversation summary."
    )

    # If neither memory layer contains anything useful, avoid an
    # unnecessary LLM call and return the deterministic fallback.
    if (
        not history
        and not conversation_summary
    ):
        return MEMORY_NO_ANSWER

    system_prompt = load_prompt(
        "memory_answer.txt"
    )

    user_prompt = f"""
CONVERSATION SUMMARY

{summary_context}

RECENT CONVERSATION

{conversation_context}

CURRENT USER MESSAGE

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

    content = (
        response
        .choices[0]
        .message
        .content
    )

    if not content:
        raise MemoryAnswerError(
            "Groq returned an empty memory answer."
        )

    answer = content.strip()

    if not answer:
        raise MemoryAnswerError(
            "Groq returned an empty memory answer."
        )

    return answer