from datetime import datetime, timezone
from typing import Any

from app.db.supabase import get_supabase_client
from app.schemas.document import DocumentChunk


def get_document_by_source(
    source_name: str,
) -> dict[str, Any] | None:
    """
    Find an existing knowledge document by source filename.

    Harbor uses this to decide whether a document is new,
    unchanged, or needs to be re-indexed.
    """

    supabase = get_supabase_client()

    response = (
        supabase
        .table("knowledge_documents")
        .select(
            "id,source_name,content_hash,status"
        )
        .eq(
            "source_name",
            source_name,
        )
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]


def create_document(
    source_name: str,
    file_type: str,
    content_hash: str,
    metadata: dict[str, Any],
) -> str:
    """Create one source-document record in Supabase."""

    supabase = get_supabase_client()

    now = datetime.now(
        timezone.utc
    ).isoformat()

    response = (
        supabase
        .table("knowledge_documents")
        .insert(
            {
                "source_name": source_name,
                "file_type": file_type,
                "content_hash": content_hash,
                "metadata": metadata,
                "status": "indexed",
                "last_indexed_at": now,
            }
        )
        .execute()
    )

    if not response.data:
        raise RuntimeError(
            "Could not create knowledge document."
        )

    return response.data[0]["id"]


def update_document(
    document_id: str,
    content_hash: str,
    metadata: dict[str, Any],
) -> None:
    """Update metadata and hash for a changed source document."""

    supabase = get_supabase_client()

    now = datetime.now(
        timezone.utc
    ).isoformat()

    (
        supabase
        .table("knowledge_documents")
        .update(
            {
                "content_hash": content_hash,
                "metadata": metadata,
                "status": "indexed",
                "updated_at": now,
                "last_indexed_at": now,
            }
        )
        .eq(
            "id",
            document_id,
        )
        .execute()
    )


def delete_document_chunks(
    document_id: str,
) -> None:
    """Delete old chunk vectors belonging to one document."""

    supabase = get_supabase_client()

    (
        supabase
        .table("knowledge_chunks")
        .delete()
        .eq(
            "document_id",
            document_id,
        )
        .execute()
    )


def insert_chunks(
    document_id: str,
    chunks: list[DocumentChunk],
    embeddings: list[list[float]],
) -> None:
    """
    Store chunks and their corresponding embedding vectors.

    Counts must match to prevent a chunk from being paired with
    the wrong embedding.
    """

    if len(chunks) != len(embeddings):
        raise ValueError(
            "Chunk count and embedding count must match."
        )

    if not chunks:
        return

    supabase = get_supabase_client()

    rows: list[dict[str, Any]] = []

    for chunk, embedding in zip(
        chunks,
        embeddings,
        strict=True,
    ):
        rows.append(
            {
                "id": chunk.chunk_id,
                "document_id": document_id,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "metadata": chunk.metadata,
                "embedding": embedding,
            }
        )

    # Batch inserts avoid excessively large HTTP requests.
    batch_size = 100

    for start in range(
        0,
        len(rows),
        batch_size,
    ):
        batch = rows[
            start:start + batch_size
        ]

        (
            supabase
            .table("knowledge_chunks")
            .insert(batch)
            .execute()
        )


def similarity_search(
    query_embedding: list[float],
    match_threshold: float = 0.35,
    match_count: int = 5,
) -> list[dict[str, Any]]:
    """
    Return chunks whose embeddings are semantically similar
    to the supplied query embedding.
    """

    supabase = get_supabase_client()

    response = (
        supabase
        .rpc(
            "match_knowledge_chunks",
            {
                "query_embedding": query_embedding,
                "match_threshold": match_threshold,
                "match_count": match_count,
            },
        )
        .execute()
    )

    return response.data or []