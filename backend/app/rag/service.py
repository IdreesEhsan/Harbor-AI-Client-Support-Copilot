from app.rag.context import build_context
from app.rag.generator import generate_grounded_answer
from app.rag.retriever import retrieve_chunks
from app.schemas.rag import (
    Citation,
    RAGResponse,
)


NO_ANSWER_MESSAGE = (
    "I don't have enough information in the Harbor "
    "knowledge base to answer that question."
)


def answer_question(
    question: str,
    match_threshold: float = 0.35,
    match_count: int = 5,
) -> RAGResponse:
    """
    Run Harbor's complete Phase 6 RAG pipeline.

    Groq is only called when retrieval finds qualifying knowledge,
    reducing hallucination risk, latency, and unnecessary API usage.
    """

    chunks = retrieve_chunks(
        question=question,
        match_threshold=match_threshold,
        match_count=match_count,
    )

    if not chunks:
        return RAGResponse(
            answer=NO_ANSWER_MESSAGE,
            grounded=False,
            citations=[],
            retrieved_chunks=0,
        )

    context = build_context(
        chunks
    )

    answer = generate_grounded_answer(
        question=question,
        context=context,
    )

    citations = [
        Citation(
            source=chunk.source_name,
            chunk_index=chunk.chunk_index,
            similarity=chunk.similarity,
            metadata=chunk.metadata,
        )
        for chunk in chunks
    ]

    return RAGResponse(
        answer=answer,
        grounded=True,
        citations=citations,
        retrieved_chunks=len(chunks),
    )