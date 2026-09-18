import logging
from typing import Any

from app.db.supabase import (
    get_supabase_client,
)


logger = logging.getLogger(
    "harbor.rag.analytics"
)


# ============================================================
# QUERY ANALYTICS
# ============================================================

def record_rag_query(
    *,
    original_query: str,
    rewritten_query: str,
    grounded: bool,
    retrieved_chunks: int,
    top_similarity: float | None,
    knowledge_gap: bool,
    gap_reason: str | None,
    source_names: list[str],
) -> None:
    """
    Persist lightweight production RAG analytics.

    Analytics failures never prevent a customer response.
    """

    try:
        client = (
            get_supabase_client()
        )

        payload: dict[
            str,
            Any,
        ] = {
            "original_query":
                original_query,

            "rewritten_query":
                rewritten_query,

            "grounded":
                grounded,

            "retrieved_chunks":
                retrieved_chunks,

            "top_similarity":
                top_similarity,

            "knowledge_gap":
                knowledge_gap,

            "gap_reason":
                gap_reason,

            "source_names":
                source_names,
        }

        (
            client
            .table(
                "rag_query_analytics"
            )
            .insert(
                payload
            )
            .execute()
        )

    except Exception:
        logger.exception(
            (
                "Failed to record RAG analytics. "
                "Customer response is unaffected."
            )
        )


# ============================================================
# KNOWLEDGE GAPS
# ============================================================

def list_knowledge_gaps(
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
            "rag_query_analytics"
        )
        .select("*")
        .eq(
            "knowledge_gap",
            True,
        )
        .order(
            "created_at",
            desc=True,
        )
        .limit(limit)
        .execute()
    )

    return (
        response.data
        or []
    )


# ============================================================
# FEEDBACK
# ============================================================

def create_rag_feedback(
    *,
    user_id: str,
    question: str,
    answer: str,
    rating: str,
    comment: str | None,
    source_names: list[str],
) -> dict[str, Any]:
    if rating not in {
        "positive",
        "negative",
    }:
        raise ValueError(
            "Unsupported RAG feedback rating."
        )

    client = (
        get_supabase_client()
    )

    response = (
        client
        .table(
            "rag_feedback"
        )
        .insert(
            {
                "user_id":
                    user_id,

                "question":
                    question.strip(),

                "answer":
                    answer.strip(),

                "rating":
                    rating,

                "comment":
                    (
                        comment.strip()
                        if comment
                        else None
                    ),

                "source_names":
                    source_names,
            }
        )
        .execute()
    )

    if not response.data:
        raise RuntimeError(
            "Could not save RAG feedback."
        )

    return (
        response.data[0]
    )


def list_rag_feedback(
    *,
    rating: str | None = None,
    limit: int = 100,
) -> list[
    dict[str, Any]
]:
    if limit <= 0:
        raise ValueError(
            "limit must be greater than zero."
        )

    if (
        rating is not None
        and rating not in {
            "positive",
            "negative",
        }
    ):
        raise ValueError(
            (
                "rating must be positive "
                "or negative."
            )
        )

    client = (
        get_supabase_client()
    )

    query = (
        client
        .table(
            "rag_feedback"
        )
        .select("*")
    )

    if rating:
        query = (
            query.eq(
                "rating",
                rating,
            )
        )

    response = (
        query
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


# ============================================================
# DASHBOARD SUMMARY
# ============================================================

def get_rag_analytics_summary() -> dict[
    str,
    Any
]:
    client = (
        get_supabase_client()
    )


    query_response = (
        client
        .table(
            "rag_query_analytics"
        )
        .select(
            (
                "grounded,"
                "knowledge_gap,"
                "retrieved_chunks"
            )
        )
        .execute()
    )


    feedback_response = (
        client
        .table(
            "rag_feedback"
        )
        .select(
            "rating"
        )
        .execute()
    )


    rows = (
        query_response.data
        or []
    )


    feedback_rows = (
        feedback_response.data
        or []
    )


    total = (
        len(rows)
    )


    grounded_count = sum(
        1
        for row
        in rows
        if row.get(
            "grounded"
        )
    )


    gap_count = sum(
        1
        for row
        in rows
        if row.get(
            "knowledge_gap"
        )
    )


    average_chunks = (
        sum(
            int(
                row.get(
                    "retrieved_chunks"
                )
                or 0
            )
            for row
            in rows
        )
        / total

        if total
        else 0.0
    )


    positive_feedback = sum(
        1
        for row
        in feedback_rows
        if row.get(
            "rating"
        ) == "positive"
    )


    negative_feedback = sum(
        1
        for row
        in feedback_rows
        if row.get(
            "rating"
        ) == "negative"
    )


    total_feedback = (
        len(
            feedback_rows
        )
    )


    return {
        "total_queries":
            total,

        "grounded_queries":
            grounded_count,

        "knowledge_gaps":
            gap_count,

        "grounded_rate":
            (
                round(
                    grounded_count
                    / total,
                    4,
                )
                if total
                else 0.0
            ),

        "knowledge_gap_rate":
            (
                round(
                    gap_count
                    / total,
                    4,
                )
                if total
                else 0.0
            ),

        "average_retrieved_chunks":
            round(
                average_chunks,
                2,
            ),

        "total_feedback":
            total_feedback,

        "positive_feedback":
            positive_feedback,

        "negative_feedback":
            negative_feedback,

        "positive_feedback_rate":
            (
                round(
                    positive_feedback
                    / total_feedback,
                    4,
                )
                if total_feedback
                else 0.0
            ),
    }