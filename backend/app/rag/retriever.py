from app.rag.embeddings import embed_query
from app.rag.vector_store import similarity_search
from app.schemas.rag import RetrievedChunk


def retrieve_chunks(
    question: str,
    match_threshold: float = 0.35,
    match_count: int = 5,
) -> list[RetrievedChunk]:
    """
    Embed the user's question and retrieve relevant Harbor
    knowledge-base chunks from Supabase pgvector.
    """

    question = question.strip()

    if not question:
        raise ValueError(
            "Question cannot be empty."
        )

    query_embedding = embed_query(
        question
    )

    rows = similarity_search(
        query_embedding=query_embedding,
        match_threshold=match_threshold,
        match_count=match_count,
    )

    return [
        RetrievedChunk(
            id=str(row["id"]),
            document_id=str(
                row["document_id"]
            ),
            source_name=row["source_name"],
            content=row["content"],
            chunk_index=row["chunk_index"],
            similarity=float(
                row["similarity"]
            ),
            metadata=row.get(
                "metadata"
            ) or {},
        )
        for row in rows
    ]