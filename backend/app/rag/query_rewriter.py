import logging
import re

from app.core.config import (
    get_settings,
)

from app.rag.generator import (
    get_groq_client,
)


settings = get_settings()

logger = logging.getLogger(
    "harbor.rag.query_rewriter"
)


# ============================================================
# CONSTANTS
# ============================================================

MIN_REWRITE_LENGTH = 3

MAX_REWRITTEN_QUERY_LENGTH = 500


# ============================================================
# SIMPLE QUERY CHECK
# ============================================================

def _needs_rewrite(
    question: str,
) -> bool:
    """
    Decide whether retrieval would benefit from query rewriting.

    Clear, sufficiently descriptive questions are left alone to
    avoid unnecessary LLM latency and cost.
    """

    cleaned = (
        question.strip()
    )

    words = re.findall(
        r"\b[\w'-]+\b",
        cleaned,
    )

    if len(words) <= MIN_REWRITE_LENGTH:
        return True

    vague_phrases = {
        "what about that",
        "how does that work",
        "tell me about it",
        "what about refunds",
        "what about billing",
        "can i do that",
        "how long is it",
    }

    if (
        cleaned.lower()
        in vague_phrases
    ):
        return True

    return False


# ============================================================
# QUERY REWRITING
# ============================================================

def rewrite_retrieval_query(
    question: str,
) -> str:
    """
    Rewrite vague standalone questions into concise search queries.

    Important:
    - This does NOT answer the question.
    - This does NOT add factual information.
    - The rewritten text is used only for retrieval.
    - The original question is still sent to the grounded answer
      generator.
    """

    if not isinstance(
        question,
        str,
    ):
        raise TypeError(
            "Question must be a string."
        )

    question = (
        question.strip()
    )

    if not question:
        raise ValueError(
            "Question cannot be empty."
        )


    # --------------------------------------------------------
    # Avoid an unnecessary LLM call for already-good queries
    # --------------------------------------------------------

    if not _needs_rewrite(
        question
    ):
        return question


    system_prompt = """
You rewrite customer-support questions for document retrieval.

Your task is NOT to answer the question.

Rewrite the customer's message into one short, explicit search query
that would retrieve the most relevant support-policy or knowledge-base
content.

Rules:
- Preserve the customer's original meaning.
- Do not invent facts.
- Do not assume missing account details.
- Do not answer the question.
- Do not add company policies that the user did not mention.
- Return only the rewritten search query.
- Keep it concise.
""".strip()


    user_prompt = f"""
CUSTOMER QUESTION

{question}

Rewrite this as a concise Harbor knowledge-base search query.
""".strip()


    try:
        client = (
            get_groq_client()
        )

        response = (
            client.chat.completions.create(
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

        rewritten = (
            response
            .choices[0]
            .message
            .content
            or ""
        ).strip()


        if not rewritten:
            return question


        if (
            len(rewritten)
            > MAX_REWRITTEN_QUERY_LENGTH
        ):
            return question


        logger.info(
            (
                "RAG retrieval query rewritten | "
                "original_length=%s | "
                "rewritten_length=%s"
            ),
            len(question),
            len(rewritten),
        )


        return rewritten


    except Exception:
        logger.exception(
            (
                "Query rewriting failed; "
                "falling back to original query."
            )
        )

        return question