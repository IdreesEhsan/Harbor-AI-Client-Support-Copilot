from app.agent.streaming import (
    emit_stream_token,
    has_stream_emitter,
)

from app.core.config import (
    get_settings,
)

from app.core.prompts import (
    load_prompt,
)

from app.rag.generator import (
    get_groq_client,
)

from app.services.memory_service import (
    history_to_text,
)


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
    history: list[
        dict[str, str]
    ] | None = None,
    conversation_summary: str | None = None,
) -> str:
    """
    Answer a question using Harbor's conversation memory.

    When Harbor's streaming endpoint is active, Groq's
    generated response is streamed incrementally.

    Conversation memory remains contextual user-provided
    information and is not treated as authoritative Harbor
    knowledge-base evidence.
    """

    question = (
        question.strip()
    )


    if not question:
        raise ValueError(
            "Question cannot be empty."
        )


    history = (
        history
        or []
    )


    conversation_context = (
        history_to_text(
            history
        )
    )


    summary_context = (
        conversation_summary.strip()
        if conversation_summary
        else (
            "No previous "
            "conversation summary."
        )
    )


    # ========================================================
    # NO MEMORY AVAILABLE
    # ========================================================

    if (
        not history
        and not conversation_summary
    ):
        return MEMORY_NO_ANSWER


    system_prompt = (
        load_prompt(
            "memory_answer.txt"
        )
    )


    user_prompt = f"""
CONVERSATION SUMMARY

{summary_context}

RECENT CONVERSATION

{conversation_context}

CURRENT USER MESSAGE

{question}
""".strip()


    client = (
        get_groq_client()
    )


    # ========================================================
    # STREAMING MODE
    # ========================================================

    if has_stream_emitter():

        stream = (
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
                            user_prompt,
                    },
                ],

                temperature=0.0,

                stream=True,
            )
        )


        answer_parts: list[str] = []


        for chunk in stream:

            if not chunk.choices:
                continue


            delta = (
                chunk
                .choices[0]
                .delta
                .content
                or ""
            )


            if not delta:
                continue


            answer_parts.append(
                delta
            )


            emit_stream_token(
                delta
            )


        answer = "".join(
            answer_parts
        ).strip()


    # ========================================================
    # NORMAL MODE
    # ========================================================

    else:

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
                            user_prompt,
                    },
                ],

                temperature=0.0,
            )
        )


        answer = (
            response
            .choices[0]
            .message
            .content
            or ""
        ).strip()


    # ========================================================
    # VALIDATION
    # ========================================================

    if not answer:
        raise MemoryAnswerError(
            "Groq returned an empty memory answer."
        )


    return answer