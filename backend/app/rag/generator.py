from functools import lru_cache

from groq import Groq

from app.core.config import get_settings
from app.core.prompts import load_prompt


settings = get_settings()


@lru_cache(maxsize=1)
def get_groq_client() -> Groq:
    """
    Create one reusable Groq client.

    Keeping one client instance avoids recreating the SDK object for
    every Harbor RAG request.
    """

    return Groq(
        api_key=settings.groq_api_key
    )


def generate_grounded_answer(
    question: str,
    context: str,
) -> str:
    """
    Generate a support answer from retrieved Harbor knowledge only.
    """

    question = question.strip()
    context = context.strip()

    if not question:
        raise ValueError(
            "Question cannot be empty."
        )

    if not context:
        raise ValueError(
            "Grounded generation requires retrieval context."
        )

    system_prompt = load_prompt(
        "support_system.txt"
    )

    user_prompt = f"""
KNOWLEDGE-BASE CONTEXT

{context}

USER QUESTION

{question}

Answer the user's question using only the knowledge-base context above.
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
        temperature=0.1,
    )

    answer = (
        response
        .choices[0]
        .message
        .content
    )

    if not answer or not answer.strip():
        raise RuntimeError(
            "Groq returned an empty response."
        )

    return answer.strip()