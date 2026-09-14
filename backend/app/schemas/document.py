from typing import Any

from pydantic import BaseModel, Field


class LoadedDocument(BaseModel):
    """
    Standard representation used after loading any supported document type.

    Using one shared schema means the chunking pipeline does not need
    file-type-specific logic after extraction is complete.
    """

    source: str
    file_type: str
    content: str

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )


class DocumentChunk(BaseModel):
    """
    Standard representation of a retrieval-ready document chunk.

    These chunks will later be embedded and stored in Supabase pgvector.
    """

    chunk_id: str
    source: str
    content: str
    chunk_index: int

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )