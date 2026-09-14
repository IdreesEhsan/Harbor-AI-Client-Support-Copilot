import json
from pathlib import Path

from app.ingestion.chunker import (
    ChunkingStrategy,
    chunk_document,
)
from app.ingestion.cleaner import (
    clean_text,
)
from app.ingestion.loaders import (
    load_document,
)


def process_document(
    file_path: Path,
    output_directory: Path,
    chunking_strategy: ChunkingStrategy = "recursive",
    chunk_size: int = 800,
    overlap: int = 120,
) -> Path:
    """
    Run Harbor's complete local ingestion pipeline for one document.

    Output remains local JSON during Phase 4 so chunk quality can
    be inspected before introducing embeddings and vector storage.
    """

    document = load_document(
        file_path
    )

    # All file loaders feed the same cleanup stage for consistency.
    document.content = clean_text(
        document.content
    )

    chunks = chunk_document(
        document=document,
        strategy=chunking_strategy,
        chunk_size=chunk_size,
        overlap=overlap,
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_directory
        / (
            f"{file_path.stem}"
            f"_{chunking_strategy}"
            f"_{chunk_size}"
            f"_{overlap}.json"
        )
    )

    payload = {
        "source": document.source,
        "file_type": document.file_type,
        "metadata": document.metadata,
        "chunking": {
            "strategy": chunking_strategy,
            "chunk_size": chunk_size,
            "overlap": overlap,
        },
        "chunk_count": len(chunks),
        "chunks": [
            chunk.model_dump()
            for chunk in chunks
        ],
    }

    output_path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return output_path