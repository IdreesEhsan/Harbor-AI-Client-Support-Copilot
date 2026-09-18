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


# ============================================================
# SAFE FALLBACK RESPONSES
# ============================================================

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
# ROLE NORMALIZATION
# ============================================================

def _normalize_requester_role(
    requester_role: str,
) -> str:
    """
    Normalize the caller's role before retrieval.

    Customers may retrieve only public knowledge.

    support_agent/admin may retrieve:
    - public knowledge
    - staff_only knowledge

    Unknown roles are treated as customers.
    """

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
# SOURCE HELPERS
# ============================================================

def _unique_sources(
    chunks,
) -> list[str]:
    """
    Extract unique source names from retrieved chunks while
    preserving their original order.
    """

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
    """
    Return the highest hybrid relevance score among the
    retrieved chunks.
    """

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
    """
    Convert retrieved chunks into Harbor citation objects.
    """

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
    record_analytics: bool = True,
) -> RAGResponse:
    """
    Execute Harbor's complete grounded RAG pipeline.

    Flow:

        Original question
              ↓
        Retrieval query rewriting
              ↓
        Role-aware hybrid retrieval
              ↓
        Vector + keyword search
              ↓
        Reranking
              ↓
        Evidence available?
          ┌───────────────┐
          │               │
         Yes              No
          │               │
          ↓               ↓
    Conflict check     No-answer
          │               │
       conflict?       Gap analytics
      ┌────┴────┐
      │         │
     Yes        No
      │         │
      ↓         ↓
 Safe conflict  Build context
   response          ↓
      │        Grounded Groq answer
      │              ↓
      └────────→ Citations
                     ↓
                  Analytics

    The optional record_analytics flag is used by Harbor's
    automated evaluation system so test cases do not pollute
    production RAG analytics.
    """

    # --------------------------------------------------------
    # 1. Validate question
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # 2. Normalize requester role
    # --------------------------------------------------------

    requester_role = (
        _normalize_requester_role(
            requester_role
        )
    )


    # --------------------------------------------------------
    # 3. Rewrite retrieval query
    #
    # This rewritten query is used ONLY for search.
    #
    # The original user question is still used for final answer
    # generation so the user's intent is preserved.
    # --------------------------------------------------------

    retrieval_query = (
        rewrite_retrieval_query(
            original_question
        )
    )


    # --------------------------------------------------------
    # 4. Role-aware hybrid retrieval
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
    # 5. Knowledge-gap handling
    # --------------------------------------------------------

    if not chunks:

        if record_analytics:
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


        logger.info(
            (
                "RAG knowledge gap | "
                "role=%s | "
                "rewritten=%s"
            ),
            requester_role,
            (
                retrieval_query
                != original_question
            ),
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
    # 6. Conflict detection
    #
    # The conflict detector checks whether evidence from
    # multiple active policies directly contradicts itself.
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

        # Genuine conflicts remain useful even during automated
        # evaluation, so conflict logging is intentionally NOT
        # disabled by record_analytics=False.
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


        if record_analytics:
            record_rag_query(
                original_query=(
                    original_question
                ),

                rewritten_query=(
                    retrieval_query
                ),

                grounded=False,

                retrieved_chunks=(
                    len(
                        chunks
                    )
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
                "logical_keys=%s | "
                "reason=%s"
            ),
            requester_role,
            conflict.source_names,
            conflict.logical_keys,
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
                    len(
                        chunks
                    )
                ),
            )
        )


    # --------------------------------------------------------
    # 7. Build grounded context
    # --------------------------------------------------------

    context = (
        build_context(
            chunks
        )
    )


    # --------------------------------------------------------
    # 8. Generate answer using ORIGINAL question
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


    # --------------------------------------------------------
    # 9. Build citations
    # --------------------------------------------------------

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


    top_similarity = (
        _top_similarity(
            chunks
        )
    )


    # --------------------------------------------------------
    # 10. Production analytics
    #
    # Automated evaluation calls Harbor with:
    #
    #     record_analytics=False
    #
    # so evaluation runs do not distort real customer metrics.
    # --------------------------------------------------------

    if record_analytics:
        record_rag_query(
            original_query=(
                original_question
            ),

            rewritten_query=(
                retrieval_query
            ),

            grounded=True,

            retrieved_chunks=(
                len(
                    chunks
                )
            ),

            top_similarity=(
                top_similarity
            ),

            knowledge_gap=False,

            gap_reason=None,

            source_names=(
                sources
            ),
        )


    # --------------------------------------------------------
    # 11. Logging
    # --------------------------------------------------------

    logger.info(
        (
            "RAG request completed | "
            "role=%s | "
            "rewritten=%s | "
            "grounded=true | "
            "chunks=%s | "
            "top_similarity=%s | "
            "analytics=%s"
        ),
        requester_role,
        (
            retrieval_query
            != original_question
        ),
        len(
            chunks
        ),
        top_similarity,
        record_analytics,
    )


    # --------------------------------------------------------
    # 12. Final response
    # --------------------------------------------------------

    return (
        RAGResponse(
            answer=(
                answer
            ),

            grounded=True,

            citations=(
                citations
            ),

            retrieved_chunks=(
                len(
                    chunks
                )
            ),
        )
    )