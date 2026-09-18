import logging

from app.rag.analytics import (
    record_rag_query,
)

from app.rag.conflict_detector import (
    detect_policy_conflict,
    record_policy_conflict,
)

from app.rag.context import (
    build_context,
)

from app.rag.generator import (
    generate_grounded_answer,
)

from app.rag.query_rewriter import (
    rewrite_retrieval_query,
)

from app.rag.retriever import (
    retrieve_chunks,
)

from app.schemas.rag import (
    Citation,
    RAGResponse,
)


logger = logging.getLogger(
    "harbor.rag.service"
)


NO_ANSWER_MESSAGE = (
    "I don't have enough information in the Harbor "
    "knowledge base to answer that question."
)


CONFLICT_MESSAGE = (
    "I found conflicting information in Harbor's active "
    "knowledge base, so I can't provide a reliable answer "
    "to that question yet. A Harbor support agent should "
    "review the conflicting policies."
)


# ============================================================
# HELPERS
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


def _unique_sources(
    chunks,
) -> list[str]:
    sources: list[str] = []

    for chunk in chunks:
        source = (
            chunk.source_name
        )

        if (
            source
            and source not in sources
        ):
            sources.append(
                source
            )

    return sources


def _top_similarity(
    chunks,
) -> float | None:
    if not chunks:
        return None

    return max(
        float(
            chunk.similarity
        )

        for chunk
        in chunks
    )


def _build_citations(
    chunks,
) -> list[
    Citation
]:
    return [
        Citation(
            source=(
                chunk.source_name
            ),

            chunk_index=(
                chunk.chunk_index
            ),

            similarity=(
                chunk.similarity
            ),

            metadata=(
                chunk.metadata
            ),
        )

        for chunk
        in chunks
    ]


# ============================================================
# COMPLETE RAG PIPELINE
# ============================================================

def answer_question(
    question: str,
    match_threshold: float = 0.35,
    match_count: int = 5,
    requester_role: str = "customer",
) -> RAGResponse:
    if not isinstance(
        question,
        str,
    ):
        raise TypeError(
            "Question must be a string."
        )

    original_question = (
        question.strip()
    )

    if not original_question:
        raise ValueError(
            "Question cannot be empty."
        )


    requester_role = (
        _normalize_requester_role(
            requester_role
        )
    )


    # --------------------------------------------------------
    # 1. Retrieval query rewriting
    # --------------------------------------------------------

    retrieval_query = (
        rewrite_retrieval_query(
            original_question
        )
    )


    # --------------------------------------------------------
    # 2. Role-aware hybrid retrieval
    # --------------------------------------------------------

    chunks = (
        retrieve_chunks(
            question=(
                retrieval_query
            ),

            match_threshold=(
                match_threshold
            ),

            match_count=(
                match_count
            ),

            requester_role=(
                requester_role
            ),
        )
    )


    # --------------------------------------------------------
    # 3. Knowledge gap
    # --------------------------------------------------------

    if not chunks:
        record_rag_query(
            original_query=(
                original_question
            ),

            rewritten_query=(
                retrieval_query
            ),

            grounded=False,

            retrieved_chunks=0,

            top_similarity=None,

            knowledge_gap=True,

            gap_reason=(
                "No qualifying knowledge-base "
                "chunks were retrieved."
            ),

            source_names=[],
        )


        return (
            RAGResponse(
                answer=(
                    NO_ANSWER_MESSAGE
                ),

                grounded=False,

                citations=[],

                retrieved_chunks=0,
            )
        )


    # --------------------------------------------------------
    # 4. Conflict detection
    # --------------------------------------------------------

    conflict = (
        detect_policy_conflict(
            question=(
                original_question
            ),

            chunks=chunks,
        )
    )


    if conflict.detected:
        record_policy_conflict(
            question=(
                original_question
            ),

            requester_role=(
                requester_role
            ),

            result=(
                conflict
            ),
        )


        record_rag_query(
            original_query=(
                original_question
            ),

            rewritten_query=(
                retrieval_query
            ),

            grounded=False,

            retrieved_chunks=(
                len(chunks)
            ),

            top_similarity=(
                _top_similarity(
                    chunks
                )
            ),

            knowledge_gap=True,

            gap_reason=(
                "Conflicting active knowledge "
                "was retrieved."
            ),

            source_names=(
                _unique_sources(
                    chunks
                )
            ),
        )


        logger.warning(
            (
                "RAG conflict detected | "
                "role=%s | "
                "sources=%s | "
                "reason=%s"
            ),
            requester_role,
            conflict.source_names,
            conflict.reason,
        )


        return (
            RAGResponse(
                answer=(
                    CONFLICT_MESSAGE
                ),

                grounded=False,

                citations=(
                    _build_citations(
                        chunks
                    )
                ),

                retrieved_chunks=(
                    len(chunks)
                ),
            )
        )


    # --------------------------------------------------------
    # 5. Build context
    # --------------------------------------------------------

    context = (
        build_context(
            chunks
        )
    )


    # --------------------------------------------------------
    # 6. Grounded answer
    # --------------------------------------------------------

    answer = (
        generate_grounded_answer(
            question=(
                original_question
            ),

            context=(
                context
            ),
        )
    )


    citations = (
        _build_citations(
            chunks
        )
    )


    sources = (
        _unique_sources(
            chunks
        )
    )


    # --------------------------------------------------------
    # 7. Analytics
    # --------------------------------------------------------

    record_rag_query(
        original_query=(
            original_question
        ),

        rewritten_query=(
            retrieval_query
        ),

        grounded=True,

        retrieved_chunks=(
            len(chunks)
        ),

        top_similarity=(
            _top_similarity(
                chunks
            )
        ),

        knowledge_gap=False,

        gap_reason=None,

        source_names=(
            sources
        ),
    )


    logger.info(
        (
            "RAG request completed | "
            "role=%s | "
            "rewritten=%s | "
            "grounded=true | "
            "chunks=%s | "
            "top_similarity=%s"
        ),
        requester_role,
        (
            retrieval_query
            != original_question
        ),
        len(chunks),
        _top_similarity(
            chunks
        ),
    )


    return (
        RAGResponse(
            answer=answer,

            grounded=True,

            citations=(
                citations
            ),

            retrieved_chunks=(
                len(chunks)
            ),
        )
    )