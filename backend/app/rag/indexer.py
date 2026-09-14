from pathlib import Path

from app.ingestion.chunker import (
    ChunkingStrategy,
    chunk_document,
)
from app.ingestion.cleaner import clean_text
from app.ingestion.hashing import calculate_content_hash
from app.ingestion.loaders import load_document
from app.rag.embeddings import embed_texts
from app.rag.vector_store import (
    create_document,
    delete_document_chunks,
    get_document_by_source,
    insert_chunks,
    update_document,
)


def index_document(
    file_path: Path,
    strategy: ChunkingStrategy = "recursive",
    chunk_size: int = 800,
    overlap: int = 120,
) -> dict:
    """
    Process one document and synchronize it with pgvector.

    Unchanged documents are skipped to prevent duplicate vector
    records and unnecessary embedding work.
    """

    document = load_document(
        file_path
    )

    document.content = clean_text(
        document.content
    )

    content_hash = calculate_content_hash(
        document.content
    )

    existing_document = get_document_by_source(
        document.source
    )

    if (
        existing_document
        and existing_document["content_hash"] == content_hash
    ):
        return {
            "source": document.source,
            "status": "skipped",
            "reason": "Document content has not changed.",
        }

    chunks = chunk_document(
        document=document,
        strategy=strategy,
        chunk_size=chunk_size,
        overlap=overlap,
    )

    texts = [
        chunk.content
        for chunk in chunks
    ]

    embeddings = embed_texts(
        texts
    )

    if existing_document:
        document_id = existing_document["id"]

        # Remove stale vectors before storing replacement content.
        delete_document_chunks(
            document_id
        )

        update_document(
            document_id=document_id,
            content_hash=content_hash,
            metadata=document.metadata,
        )

    else:
        document_id = create_document(
            source_name=document.source,
            file_type=document.file_type,
            content_hash=content_hash,
            metadata=document.metadata,
        )

    insert_chunks(
        document_id=document_id,
        chunks=chunks,
        embeddings=embeddings,
    )

    return {
        "source": document.source,
        "status": "indexed",
        "document_id": document_id,
        "chunks": len(chunks),
    }