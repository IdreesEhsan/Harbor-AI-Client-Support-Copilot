from typing import Any

from app.rag.embeddings import (
    embed_query,
)

from app.rag.vector_store import (
    keyword_search,
    similarity_search,
)

from app.schemas.rag import (
    RetrievedChunk,
)


VECTOR_WEIGHT = 0.70

KEYWORD_WEIGHT = 0.30


# ============================================================
# ROLE
# ============================================================

def _normalize_requester_role(
    requester_role: str,
) -> str:
    if (
        isinstance(
            requester_role,
            str,
        )
        and requester_role
        .strip()
        .lower()
        in {
            "support_agent",
            "admin",
        }
    ):
        return (
            requester_role
            .strip()
            .lower()
        )

    return "customer"


# ============================================================
# SCORE HELPERS
# ============================================================

def _normalize_keyword_scores(
    rows: list[
        dict[str, Any]
    ],
) -> dict[str, float]:
    if not rows:
        return {}

    max_score = max(
        float(
            row.get(
                "keyword_score",
                0.0,
            )
        )

        for row
        in rows
    )

    if max_score <= 0:
        return {
            str(
                row["id"]
            ): 0.0

            for row
            in rows
        }

    return {
        str(
            row["id"]
        ):
            (
                float(
                    row.get(
                        "keyword_score",
                        0.0,
                    )
                )
                / max_score
            )

        for row
        in rows
    }


# ============================================================
# MERGE + RERANK
# ============================================================

def _rerank_candidates(
    *,
    vector_rows: list[
        dict[str, Any]
    ],
    keyword_rows: list[
        dict[str, Any]
    ],
    final_count: int,
) -> list[
    dict[str, Any]
]:
    keyword_scores = (
        _normalize_keyword_scores(
            keyword_rows
        )
    )

    candidates: dict[
        str,
        dict[str, Any]
    ] = {}


    for row in vector_rows:
        chunk_id = str(
            row[
                "id"
            ]
        )

        candidates[
            chunk_id
        ] = {
            **row,

            "_vector_similarity":
                float(
                    row.get(
                        "similarity",
                        0.0,
                    )
                ),

            "_keyword_similarity":
                0.0,
        }


    for row in keyword_rows:
        chunk_id = str(
            row[
                "id"
            ]
        )

        normalized_keyword_score = (
            keyword_scores.get(
                chunk_id,
                0.0,
            )
        )

        if chunk_id in candidates:
            candidates[
                chunk_id
            ][
                "_keyword_similarity"
            ] = (
                normalized_keyword_score
            )

        else:
            candidates[
                chunk_id
            ] = {
                **row,

                "_vector_similarity":
                    0.0,

                "_keyword_similarity":
                    normalized_keyword_score,
            }


    ranked: list[
        dict[str, Any]
    ] = []

    for candidate in (
        candidates.values()
    ):
        vector_score = float(
            candidate.get(
                "_vector_similarity",
                0.0,
            )
        )

        keyword_score = float(
            candidate.get(
                "_keyword_similarity",
                0.0,
            )
        )

        hybrid_score = (
            (
                VECTOR_WEIGHT
                * vector_score
            )
            +
            (
                KEYWORD_WEIGHT
                * keyword_score
            )
        )

        metadata = (
            candidate.get(
                "metadata"
            )
            or {}
        )

        metadata = {
            **metadata,

            "retrieval": {
                "vector_score":
                    round(
                        vector_score,
                        6,
                    ),

                "keyword_score":
                    round(
                        keyword_score,
                        6,
                    ),

                "hybrid_score":
                    round(
                        hybrid_score,
                        6,
                    ),

                "retrieval_method":
                    (
                        "hybrid"
                        if (
                            vector_score > 0
                            and keyword_score > 0
                        )
                        else (
                            "vector"
                            if vector_score > 0
                            else "keyword"
                        )
                    ),
            },
        }

        ranked.append(
            {
                **candidate,

                "metadata":
                    metadata,

                "similarity":
                    hybrid_score,
            }
        )


    ranked.sort(
        key=lambda item: float(
            item.get(
                "similarity",
                0.0,
            )
        ),
        reverse=True,
    )


    return ranked[
        :final_count
    ]


# ============================================================
# PUBLIC RETRIEVER
# ============================================================

def retrieve_chunks(
    question: str,
    match_threshold: float = 0.35,
    match_count: int = 5,
    requester_role: str = "customer",
) -> list[
    RetrievedChunk
]:
    question = (
        question.strip()
    )

    if not question:
        raise ValueError(
            "Question cannot be empty."
        )

    requester_role = (
        _normalize_requester_role(
            requester_role
        )
    )

    candidate_count = max(
        match_count * 2,
        10,
    )


    query_embedding = (
        embed_query(
            question
        )
    )


    vector_rows = (
        similarity_search(
            query_embedding=(
                query_embedding
            ),

            match_threshold=(
                match_threshold
            ),

            match_count=(
                candidate_count
            ),

            requester_role=(
                requester_role
            ),
        )
    )


    keyword_rows = (
        keyword_search(
            query=question,

            match_count=(
                candidate_count
            ),

            requester_role=(
                requester_role
            ),
        )
    )


    rows = (
        _rerank_candidates(
            vector_rows=(
                vector_rows
            ),

            keyword_rows=(
                keyword_rows
            ),

            final_count=(
                match_count
            ),
        )
    )


    return [
        RetrievedChunk(
            id=str(
                row[
                    "id"
                ]
            ),

            document_id=str(
                row[
                    "document_id"
                ]
            ),

            source_name=(
                row[
                    "source_name"
                ]
            ),

            content=(
                row[
                    "content"
                ]
            ),

            chunk_index=(
                row[
                    "chunk_index"
                ]
            ),

            similarity=float(
                row[
                    "similarity"
                ]
            ),

            metadata=(
                row.get(
                    "metadata"
                )
                or {}
            ),
        )

        for row
        in rows
    ]