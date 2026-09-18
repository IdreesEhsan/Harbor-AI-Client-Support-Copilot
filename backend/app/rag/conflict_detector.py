import json
import logging
from dataclasses import dataclass
from typing import Any

from app.core.config import (
    get_settings,
)

from app.db.supabase import (
    get_supabase_client,
)

from app.rag.generator import (
    get_groq_client,
)


settings = get_settings()


logger = logging.getLogger(
    "harbor.rag.conflict_detector"
)


# ============================================================
# RESULT
# ============================================================

@dataclass
class ConflictResult:
    detected: bool

    reason: str | None = None

    logical_keys: list[str] | None = None

    source_names: list[str] | None = None


# ============================================================
# HELPERS
# ============================================================

def _logical_keys(
    chunks,
) -> list[str]:
    keys: list[str] = []

    for chunk in chunks:
        metadata = (
            chunk.metadata
            or {}
        )

        logical_key = str(
            metadata.get(
                "logical_key",
                ""
            )
        ).strip()

        if (
            logical_key
            and logical_key
            not in keys
        ):
            keys.append(
                logical_key
            )

    return keys


def _source_names(
    chunks,
) -> list[str]:
    names: list[str] = []

    for chunk in chunks:
        source_name = str(
            chunk.source_name
            or ""
        ).strip()

        if (
            source_name
            and source_name
            not in names
        ):
            names.append(
                source_name
            )

    return names


def _build_evidence(
    chunks,
) -> str:
    sections: list[str] = []

    for index, chunk in enumerate(
        chunks,
        start=1,
    ):
        metadata = (
            chunk.metadata
            or {}
        )

        sections.append(
            (
                f"[SOURCE {index}]\n"
                f"Source: {chunk.source_name}\n"
                f"Logical key: "
                f"{metadata.get('logical_key')}\n"
                f"Category: "
                f"{metadata.get('category')}\n"
                f"Version: "
                f"{metadata.get('version')}\n"
                f"Content:\n"
                f"{chunk.content}"
            )
        )

    return (
        "\n\n".join(
            sections
        )
    )


# ============================================================
# CONFLICT CHECK
# ============================================================

def detect_policy_conflict(
    *,
    question: str,
    chunks,
) -> ConflictResult:
    """
    Detect directly contradictory retrieved policy evidence.

    We intentionally skip the LLM check when all evidence
    belongs to one logical policy.
    """

    logical_keys = (
        _logical_keys(
            chunks
        )
    )

    source_names = (
        _source_names(
            chunks
        )
    )


    if len(
        logical_keys
    ) <= 1:
        return ConflictResult(
            detected=False,

            logical_keys=(
                logical_keys
            ),

            source_names=(
                source_names
            ),
        )


    evidence = (
        _build_evidence(
            chunks
        )
    )


    system_prompt = """
You are a policy-consistency checker.

Your job is ONLY to determine whether the retrieved Harbor documents
contain directly contradictory rules that materially affect the answer
to the customer's question.

Examples of real conflicts:
- one active policy says refund window is 14 days and another says 30 days;
- one policy says a fee applies and another says the same fee does not apply;
- one policy permits an action and another prohibits that same action.

Not conflicts:
- two documents discuss different aspects of the same subject;
- one document is more detailed than another;
- one is a support procedure and one is a customer-facing explanation;
- the documents contain complementary information.

Return valid JSON only:

{
  "conflict": true or false,
  "reason": "short explanation or null"
}
""".strip()


    user_prompt = f"""
CUSTOMER QUESTION

{question}

RETRIEVED EVIDENCE

{evidence}
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

                response_format={
                    "type":
                        "json_object"
                },
            )
        )


        raw = (
            response
            .choices[0]
            .message
            .content
            or "{}"
        )


        parsed: dict[
            str,
            Any,
        ] = (
            json.loads(
                raw
            )
        )


        detected = bool(
            parsed.get(
                "conflict",
                False,
            )
        )


        reason = (
            parsed.get(
                "reason"
            )
        )


        return ConflictResult(
            detected=detected,

            reason=(
                str(
                    reason
                ).strip()
                if reason
                else None
            ),

            logical_keys=(
                logical_keys
            ),

            source_names=(
                source_names
            ),
        )


    except Exception:
        logger.exception(
            (
                "Policy conflict check failed. "
                "Continuing with normal "
                "grounded RAG behavior."
            )
        )

        return ConflictResult(
            detected=False,

            logical_keys=(
                logical_keys
            ),

            source_names=(
                source_names
            ),
        )


# ============================================================
# CONFLICT LOGGING
# ============================================================

def record_policy_conflict(
    *,
    question: str,
    requester_role: str,
    result: ConflictResult,
) -> None:
    if not result.detected:
        return

    try:
        client = (
            get_supabase_client()
        )

        (
            client
            .table(
                "rag_conflicts"
            )
            .insert(
                {
                    "question":
                        question,

                    "requester_role":
                        requester_role,

                    "reason":
                        (
                            result.reason
                            or (
                                "Conflicting active "
                                "knowledge was detected."
                            )
                        ),

                    "source_names":
                        (
                            result.source_names
                            or []
                        ),

                    "logical_keys":
                        (
                            result.logical_keys
                            or []
                        ),
                }
            )
            .execute()
        )

    except Exception:
        logger.exception(
            (
                "Failed to persist RAG "
                "conflict record."
            )
        )


def list_policy_conflicts(
    *,
    limit: int = 100,
) -> list[
    dict[str, Any]
]:
    if limit <= 0:
        raise ValueError(
            "limit must be greater than zero."
        )

    client = (
        get_supabase_client()
    )

    response = (
        client
        .table(
            "rag_conflicts"
        )
        .select("*")
        .order(
            "created_at",
            desc=True,
        )
        .limit(
            limit
        )
        .execute()
    )

    return (
        response.data
        or []
    )