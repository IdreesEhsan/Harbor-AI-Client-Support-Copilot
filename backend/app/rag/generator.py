from functools import lru_cache

from groq import Groq

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


settings = get_settings()


# ============================================================
# GROQ CLIENT
# ============================================================

@lru_cache(maxsize=1)
def get_groq_client() -> Groq:
    """
    Create one reusable Groq client.

    Keeping one client instance avoids recreating the SDK
    object for every Harbor request.
    """

    return Groq(
        api_key=(
            settings.groq_api_key
        )
    )


# ============================================================
# GROUNDED GENERATION
# ============================================================

def generate_grounded_answer(
    question: str,
    context: str,
) -> str:
    """
    Generate a grounded Harbor support answer.

    When the current request is running through Harbor's
    streaming endpoint, Groq streams generated chunks while
    this function simultaneously rebuilds the complete answer.

    For normal /agent/chat requests, Harbor preserves the
    original blocking behavior.
    """

    question = (
        question.strip()
    )

    context = (
        context.strip()
    )

    if not question:
        raise ValueError(
            "Question cannot be empty."
        )

    if not context:
        raise ValueError(
            "Grounded generation requires retrieval context."
        )


    system_prompt = (
        load_prompt(
            "support_system.txt"
        )
    )


    user_prompt = f"""
KNOWLEDGE-BASE CONTEXT

{context}

USER QUESTION

{question}

Answer the user's question using only the knowledge-base context above.
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

                temperature=0.1,

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
    # NORMAL BLOCKING MODE
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

                temperature=0.1,
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
        raise RuntimeError(
            "Groq returned an empty response."
        )


    return answer