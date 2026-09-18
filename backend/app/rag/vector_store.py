from datetime import (
    date,
    datetime,
    timezone,
)

from typing import Any

from app.db.supabase import (
    get_supabase_client,
)

from app.schemas.document import (
    DocumentChunk,
)


# ============================================================
# HELPERS
# ============================================================

def _utc_now() -> str:
    return (
        datetime.now(
            timezone.utc
        ).isoformat()
    )


def _clean_required_string(
    value: str,
    field_name: str,
) -> str:
    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            f"{field_name} must be a string."
        )

    value = (
        value.strip()
    )

    if not value:
        raise ValueError(
            f"{field_name} cannot be empty."
        )

    return value


# ============================================================
# DOCUMENT LOOKUPS
# ============================================================

def get_document_by_source(
    source_name: str,
) -> dict[str, Any] | None:
    source_name = (
        _clean_required_string(
            source_name,
            "source_name",
        )
    )

    supabase = (
        get_supabase_client()
    )

    response = (
        supabase
        .table(
            "knowledge_documents"
        )
        .select("*")
        .eq(
            "source_name",
            source_name,
        )
        .order(
            "created_at",
            desc=True,
        )
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]


def get_active_document_by_logical_key(
    logical_key: str,
) -> dict[str, Any] | None:
    logical_key = (
        _clean_required_string(
            logical_key,
            "logical_key",
        )
        .lower()
    )

    supabase = (
        get_supabase_client()
    )

    response = (
        supabase
        .table(
            "knowledge_documents"
        )
        .select("*")
        .eq(
            "logical_key",
            logical_key,
        )
        .eq(
            "is_active",
            True,
        )
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]


def get_document_by_content_hash(
    *,
    logical_key: str,
    content_hash: str,
) -> dict[str, Any] | None:
    logical_key = (
        _clean_required_string(
            logical_key,
            "logical_key",
        )
        .lower()
    )

    content_hash = (
        _clean_required_string(
            content_hash,
            "content_hash",
        )
    )

    supabase = (
        get_supabase_client()
    )

    response = (
        supabase
        .table(
            "knowledge_documents"
        )
        .select("*")
        .eq(
            "logical_key",
            logical_key,
        )
        .eq(
            "content_hash",
            content_hash,
        )
        .order(
            "created_at",
            desc=True,
        )
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]


def list_knowledge_documents(
    *,
    logical_key: str | None = None,
    active_only: bool = False,
    limit: int = 100,
) -> list[dict[str, Any]]:
    if limit <= 0:
        raise ValueError(
            "limit must be greater than zero."
        )

    supabase = (
        get_supabase_client()
    )

    query = (
        supabase
        .table(
            "knowledge_documents"
        )
        .select("*")
    )

    if logical_key:
        query = (
            query.eq(
                "logical_key",
                logical_key
                .strip()
                .lower(),
            )
        )

    if active_only:
        query = (
            query.eq(
                "is_active",
                True,
            )
        )

    response = (
        query
        .order(
            "created_at",
            desc=True,
        )
        .limit(limit)
        .execute()
    )

    return (
        response.data
        or []
    )


# ============================================================
# ACTIVE VERSION MANAGEMENT
# ============================================================

def deactivate_documents(
    *,
    logical_key: str,
) -> None:
    logical_key = (
        _clean_required_string(
            logical_key,
            "logical_key",
        )
        .lower()
    )

    supabase = (
        get_supabase_client()
    )

    (
        supabase
        .table(
            "knowledge_documents"
        )
        .update(
            {
                "is_active":
                    False,

                "updated_at":
                    _utc_now(),
            }
        )
        .eq(
            "logical_key",
            logical_key,
        )
        .eq(
            "is_active",
            True,
        )
        .execute()
    )


def activate_document(
    document_id: str,
) -> dict[str, Any]:
    document_id = (
        _clean_required_string(
            document_id,
            "document_id",
        )
    )

    supabase = (
        get_supabase_client()
    )

    response = (
        supabase
        .table(
            "knowledge_documents"
        )
        .select("*")
        .eq(
            "id",
            document_id,
        )
        .limit(1)
        .execute()
    )

    if not response.data:
        raise ValueError(
            "Knowledge document was not found."
        )

    document = (
        response.data[0]
    )

    logical_key = (
        document.get(
            "logical_key"
        )
    )

    if not logical_key:
        raise ValueError(
            (
                "Knowledge document does not "
                "have a logical key."
            )
        )

    deactivate_documents(
        logical_key=logical_key
    )

    updated = (
        supabase
        .table(
            "knowledge_documents"
        )
        .update(
            {
                "is_active":
                    True,

                "updated_at":
                    _utc_now(),
            }
        )
        .eq(
            "id",
            document_id,
        )
        .execute()
    )

    if not updated.data:
        raise RuntimeError(
            (
                "Could not activate "
                "knowledge document."
            )
        )

    return updated.data[0]


# ============================================================
# CREATE DOCUMENT
# ============================================================

def create_document(
    source_name: str,
    file_type: str,
    content_hash: str,
    metadata: dict[str, Any],
    *,
    logical_key: str | None = None,
    title: str | None = None,
    category: str = "general",
    version: str = "1.0",
    effective_date: date | str | None = None,
    uploaded_by: str | None = None,
    is_active: bool = True,
) -> str:
    source_name = (
        _clean_required_string(
            source_name,
            "source_name",
        )
    )

    file_type = (
        _clean_required_string(
            file_type,
            "file_type",
        )
    )

    content_hash = (
        _clean_required_string(
            content_hash,
            "content_hash",
        )
    )

    resolved_logical_key = (
        logical_key
        or source_name
    )

    resolved_logical_key = (
        _clean_required_string(
            resolved_logical_key,
            "logical_key",
        )
        .lower()
    )

    resolved_title = (
        title
        or source_name
    )

    resolved_title = (
        _clean_required_string(
            resolved_title,
            "title",
        )
    )

    category = (
        _clean_required_string(
            category,
            "category",
        )
        .lower()
    )

    version = (
        _clean_required_string(
            version,
            "version",
        )
    )

    if isinstance(
        effective_date,
        date,
    ):
        effective_date_value = (
            effective_date.isoformat()
        )
    else:
        effective_date_value = (
            effective_date
        )

    if is_active:
        deactivate_documents(
            logical_key=(
                resolved_logical_key
            )
        )

    supabase = (
        get_supabase_client()
    )

    now = (
        _utc_now()
    )

    payload = {
        "source_name":
            source_name,

        "file_type":
            file_type,

        "content_hash":
            content_hash,

        "metadata":
            metadata,

        "status":
            "indexed",

        "last_indexed_at":
            now,

        "logical_key":
            resolved_logical_key,

        "title":
            resolved_title,

        "category":
            category,

        "version":
            version,

        "effective_date":
            effective_date_value,

        "is_active":
            is_active,

        "uploaded_by":
            uploaded_by,
    }

    response = (
        supabase
        .table(
            "knowledge_documents"
        )
        .insert(
            payload
        )
        .execute()
    )

    if not response.data:
        raise RuntimeError(
            (
                "Could not create "
                "knowledge document."
            )
        )

    return (
        response.data[0][
            "id"
        ]
    )


# ============================================================
# LEGACY UPDATE
# ============================================================

def update_document(
    document_id: str,
    content_hash: str,
    metadata: dict[str, Any],
) -> None:
    supabase = (
        get_supabase_client()
    )

    now = (
        _utc_now()
    )

    (
        supabase
        .table(
            "knowledge_documents"
        )
        .update(
            {
                "content_hash":
                    content_hash,

                "metadata":
                    metadata,

                "status":
                    "indexed",

                "updated_at":
                    now,

                "last_indexed_at":
                    now,
            }
        )
        .eq(
            "id",
            document_id,
        )
        .execute()
    )


# ============================================================
# CHUNKS
# ============================================================

def delete_document_chunks(
    document_id: str,
) -> None:
    supabase = (
        get_supabase_client()
    )

    (
        supabase
        .table(
            "knowledge_chunks"
        )
        .delete()
        .eq(
            "document_id",
            document_id,
        )
        .execute()
    )


def insert_chunks(
    document_id: str,
    chunks: list[
        DocumentChunk
    ],
    embeddings: list[
        list[float]
    ],
) -> None:
    if (
        len(chunks)
        != len(embeddings)
    ):
        raise ValueError(
            (
                "Chunk count and embedding "
                "count must match."
            )
        )

    if not chunks:
        return

    supabase = (
        get_supabase_client()
    )

    rows: list[
        dict[str, Any]
    ] = []

    for (
        chunk,
        embedding,
    ) in zip(
        chunks,
        embeddings,
        strict=True,
    ):
        rows.append(
            {
                "id":
                    chunk.chunk_id,

                "document_id":
                    document_id,

                "chunk_index":
                    chunk.chunk_index,

                "content":
                    chunk.content,

                "metadata":
                    chunk.metadata,

                "embedding":
                    embedding,
            }
        )

    batch_size = (
        100
    )

    for start in range(
        0,
        len(rows),
        batch_size,
    ):
        batch = rows[
            start:
            start + batch_size
        ]

        (
            supabase
            .table(
                "knowledge_chunks"
            )
            .insert(
                batch
            )
            .execute()
        )


# ============================================================
# VECTOR SEARCH
# ============================================================

def similarity_search(
    query_embedding: list[float],
    match_threshold: float = 0.35,
    match_count: int = 10,
) -> list[
    dict[str, Any]
]:
    """
    Semantic vector search over active Harbor documents.
    """

    supabase = (
        get_supabase_client()
    )

    response = (
        supabase
        .rpc(
            "match_active_knowledge_chunks",
            {
                "query_embedding":
                    query_embedding,

                "match_threshold":
                    match_threshold,

                "match_count":
                    match_count,
            },
        )
        .execute()
    )

    return (
        response.data
        or []
    )


# ============================================================
# KEYWORD SEARCH
# ============================================================

def keyword_search(
    query: str,
    match_count: int = 10,
) -> list[
    dict[str, Any]
]:
    """
    PostgreSQL full-text search over active Harbor documents.
    """

    query = (
        _clean_required_string(
            query,
            "query",
        )
    )

    supabase = (
        get_supabase_client()
    )

    response = (
        supabase
        .rpc(
            "search_active_knowledge_chunks_keyword",
            {
                "search_query":
                    query,

                "match_count":
                    match_count,
            },
        )
        .execute()
    )

    return (
        response.data
        or []
    )