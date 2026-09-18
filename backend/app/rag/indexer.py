from datetime import date
from pathlib import Path
from typing import Any

from app.ingestion.chunker import (
    ChunkingStrategy,
    chunk_document,
)

from app.ingestion.cleaner import (
    clean_text,
)

from app.ingestion.hashing import (
    calculate_content_hash,
)

from app.ingestion.loaders import (
    load_document,
)

from app.rag.embeddings import (
    embed_texts,
)

from app.rag.vector_store import (
    activate_document,
    create_document,
    get_active_document_by_logical_key,
    get_document_by_content_hash,
    insert_chunks,
)


def _default_logical_key(
    file_path: Path,
) -> str:
    """
    Default stable knowledge identity.

    Explicit logical_key is preferable for versioned policies.
    """

    return (
        file_path
        .stem
        .strip()
        .lower()
        .replace(
            " ",
            "-"
        )
    )


def index_document(
    file_path: Path,
    strategy: ChunkingStrategy = "recursive",
    chunk_size: int = 800,
    overlap: int = 120,
    *,
    logical_key: str | None = None,
    title: str | None = None,
    category: str = "general",
    version: str = "1.0",
    effective_date: date | str | None = None,
    uploaded_by: str | None = None,
) -> dict[str, Any]:
    """
    Index a new immutable version of one knowledge document.

    Behavior:

    1. Load + clean document.
    2. Calculate content hash.
    3. Detect duplicate content.
    4. Chunk and embed only if needed.
    5. Preserve previous document versions.
    6. Deactivate the previous active version.
    7. Store the new version as active.
    """

    file_path = Path(
        file_path
    )

    resolved_logical_key = (
        logical_key
        or _default_logical_key(
            file_path
        )
    )

    resolved_logical_key = (
        resolved_logical_key
        .strip()
        .lower()
    )

    if not resolved_logical_key:
        raise ValueError(
            "logical_key cannot be empty."
        )

    resolved_title = (
        title
        or file_path.stem
    )

    document = (
        load_document(
            file_path
        )
    )

    document.content = (
        clean_text(
            document.content
        )
    )

    if not document.content:
        raise ValueError(
            (
                "Document contains no "
                "indexable text."
            )
        )

    content_hash = (
        calculate_content_hash(
            document.content
        )
    )


    # ========================================================
    # Duplicate-content detection
    # ========================================================

    duplicate = (
        get_document_by_content_hash(
            logical_key=(
                resolved_logical_key
            ),
            content_hash=(
                content_hash
            ),
        )
    )

    if duplicate is not None:
        if not duplicate.get(
            "is_active"
        ):
            duplicate = (
                activate_document(
                    str(
                        duplicate[
                            "id"
                        ]
                    )
                )
            )

        return {
            "source":
                document.source,

            "status":
                "skipped",

            "reason":
                (
                    "Identical document content "
                    "already exists."
                ),

            "document_id":
                str(
                    duplicate[
                        "id"
                    ]
                ),

            "logical_key":
                resolved_logical_key,

            "version":
                duplicate.get(
                    "version"
                ),

            "is_active":
                True,
        }


    # ========================================================
    # Existing active version
    # ========================================================

    previous_active = (
        get_active_document_by_logical_key(
            resolved_logical_key
        )
    )


    # ========================================================
    # Chunk document
    # ========================================================

    version_metadata = {
        **(
            document.metadata
            or {}
        ),

        "logical_key":
            resolved_logical_key,

        "title":
            resolved_title,

        "category":
            category,

        "version":
            version,

        "effective_date":
            (
                effective_date.isoformat()
                if isinstance(
                    effective_date,
                    date,
                )
                else effective_date
            ),
    }

    document.metadata = (
        version_metadata
    )

    chunks = (
        chunk_document(
            document=document,
            strategy=strategy,
            chunk_size=chunk_size,
            overlap=overlap,
        )
    )

    if not chunks:
        raise ValueError(
            (
                "Document produced no "
                "indexable chunks."
            )
        )


    # ========================================================
    # Embeddings
    # ========================================================

    texts = [
        chunk.content
        for chunk
        in chunks
    ]

    embeddings = (
        embed_texts(
            texts
        )
    )


    # ========================================================
    # Create immutable version
    # ========================================================

    document_id = (
        create_document(
            source_name=(
                document.source
            ),

            file_type=(
                document.file_type
            ),

            content_hash=(
                content_hash
            ),

            metadata=(
                version_metadata
            ),

            logical_key=(
                resolved_logical_key
            ),

            title=(
                resolved_title
            ),

            category=(
                category
            ),

            version=(
                version
            ),

            effective_date=(
                effective_date
            ),

            uploaded_by=(
                uploaded_by
            ),

            is_active=True,
        )
    )


    # ========================================================
    # Store chunks
    # ========================================================

    insert_chunks(
        document_id=(
            document_id
        ),
        chunks=chunks,
        embeddings=embeddings,
    )


    return {
        "source":
            document.source,

        "status":
            "indexed",

        "document_id":
            document_id,

        "logical_key":
            resolved_logical_key,

        "title":
            resolved_title,

        "category":
            category,

        "version":
            version,

        "effective_date":
            (
                effective_date.isoformat()
                if isinstance(
                    effective_date,
                    date,
                )
                else effective_date
            ),

        "is_active":
            True,

        "previous_document_id":
            (
                str(
                    previous_active[
                        "id"
                    ]
                )
                if previous_active
                else None
            ),

        "chunks":
            len(
                chunks
            ),
    }