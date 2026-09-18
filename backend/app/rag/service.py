import logging

from app.rag.analytics import (
    record_rag_query,
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


# ============================================================
# HELPERS
# ============================================================

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


# ============================================================
# COMPLETE RAG PIPELINE
# ============================================================

def answer_question(
    question: str,
    match_threshold: float = 0.35,
    match_count: int = 5,
) -> RAGResponse:
    """
    Harbor grounded RAG pipeline.

    Flow:

        customer question
              ↓
        retrieval query rewrite
              ↓
        hybrid search + reranking
              ↓
        evidence check
          ┌──────────────┐
          ↓              ↓
        found          no evidence
          ↓              ↓
        context        no-answer
          ↓              ↓
        Groq           gap log
          ↓
        citations
          ↓
        analytics
    """

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
    # 1. Rewrite only the retrieval query
    # --------------------------------------------------------

    retrieval_query = (
        rewrite_retrieval_query(
            original_question
        )
    )


    # --------------------------------------------------------
    # 2. Hybrid retrieval
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
        )
    )


    # --------------------------------------------------------
    # 3. Knowledge-gap detection
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
    # 4. Build grounded context
    # --------------------------------------------------------

    context = (
        build_context(
            chunks
        )
    )


    # --------------------------------------------------------
    # 5. Generate answer using ORIGINAL question
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
    # 6. Citations
    # --------------------------------------------------------

    citations = [
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


    # --------------------------------------------------------
    # 7. Successful-query analytics
    # --------------------------------------------------------

    sources = (
        _unique_sources(
            chunks
        )
    )


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
            "rewritten=%s | "
            "grounded=true | "
            "chunks=%s | "
            "top_similarity=%s"
        ),
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