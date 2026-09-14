import uuid
from typing import Literal

from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
)

from app.schemas.document import (
    DocumentChunk,
    LoadedDocument,
)


ChunkingStrategy = Literal[
    "fixed",
    "recursive",
]


def _validate_chunk_settings(
    chunk_size: int,
    overlap: int,
) -> None:
    """Validate shared chunking parameters before any splitter runs."""

    if chunk_size <= 0:
        raise ValueError(
            "chunk_size must be greater than 0"
        )

    if overlap < 0:
        raise ValueError(
            "overlap cannot be negative"
        )

    if overlap >= chunk_size:
        raise ValueError(
            "overlap must be smaller than chunk_size"
        )


def _build_document_chunks(
    document: LoadedDocument,
    raw_chunks: list[str],
    strategy: str,
    chunk_size: int,
    overlap: int,
) -> list[DocumentChunk]:
    """
    Convert raw text segments into Harbor's standard chunk schema.

    Centralizing this step ensures all chunking strategies generate
    consistent metadata for future embeddings and evaluation.
    """

    chunks: list[DocumentChunk] = []

    for index, raw_chunk in enumerate(
        raw_chunks
    ):
        content = raw_chunk.strip()

        if not content:
            continue

        chunks.append(
            DocumentChunk(
                chunk_id=str(
                    uuid.uuid4()
                ),
                source=document.source,
                content=content,
                chunk_index=index,
                metadata={
                    **document.metadata,
                    "chunking_strategy": strategy,
                    "chunk_size": chunk_size,
                    "overlap": overlap,
                },
            )
        )

    return chunks

def fixed_chunk_document(
    document: LoadedDocument,
    chunk_size: int = 800,
    overlap: int = 120,
) -> list[DocumentChunk]:
    """
    Split text at fixed character positions.

    This simple strategy is kept as a baseline so we can later
    compare its retrieval quality against smarter splitters.
    """

    _validate_chunk_settings(
        chunk_size=chunk_size,
        overlap=overlap,
    )

    text = document.content

    raw_chunks: list[str] = []

    start = 0

    while start < len(text):
        end = start + chunk_size

        raw_chunks.append(
            text[start:end]
        )

        start += (
            chunk_size - overlap
        )

    return _build_document_chunks(
        document=document,
        raw_chunks=raw_chunks,
        strategy="fixed",
        chunk_size=chunk_size,
        overlap=overlap,
    )

def recursive_chunk_document(
    document: LoadedDocument,
    chunk_size: int = 800,
    overlap: int = 120,
) -> list[DocumentChunk]:
    """
    Split text using progressively smaller natural boundaries.

    The splitter first tries paragraphs, then lines, sentence-like
    boundaries, spaces, and finally individual characters.
    """

    _validate_chunk_settings(
        chunk_size=chunk_size,
        overlap=overlap,
    )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=[
            "\n\n",
            "\n",
            ". ",
            " ",
            "",
        ],
    )

    raw_chunks = splitter.split_text(
        document.content
    )

    return _build_document_chunks(
        document=document,
        raw_chunks=raw_chunks,
        strategy="recursive",
        chunk_size=chunk_size,
        overlap=overlap,
    )

def chunk_document(
    document: LoadedDocument,
    strategy: ChunkingStrategy = "recursive",
    chunk_size: int = 800,
    overlap: int = 120,
) -> list[DocumentChunk]:
    """
    Route document splitting through the selected strategy.

    Recursive splitting is the default because it generally preserves
    natural text boundaries better than fixed character slicing.
    """

    if strategy == "fixed":
        return fixed_chunk_document(
            document=document,
            chunk_size=chunk_size,
            overlap=overlap,
        )

    if strategy == "recursive":
        return recursive_chunk_document(
            document=document,
            chunk_size=chunk_size,
            overlap=overlap,
        )

    raise ValueError(
        f"Unsupported chunking strategy: {strategy}"
    )