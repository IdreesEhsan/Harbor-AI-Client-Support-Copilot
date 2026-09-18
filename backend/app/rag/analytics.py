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
    Persist lightweight RAG analytics.

    Analytics failures must never prevent Harbor from answering
    the customer.
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
# STAFF ANALYTICS
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
        .select(
            "*"
        )
        .eq(
            "knowledge_gap",
            True,
        )
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


def get_rag_analytics_summary() -> dict[
    str,
    Any
]:
    """
    Small dashboard-ready summary.
    """

    client = (
        get_supabase_client()
    )

    response = (
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

    rows = (
        response.data
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
    }