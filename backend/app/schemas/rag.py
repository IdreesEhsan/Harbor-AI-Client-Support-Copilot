from typing import Any

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """
    Source evidence attached to a Harbor answer.
    """

    source: str
    chunk_index: int
    similarity: float
    metadata: dict[str, Any] = Field(
        default_factory=dict
    )


class RetrievedChunk(BaseModel):
    """
    Normalized representation of one semantic-search result.
    """

    id: str
    document_id: str
    source_name: str
    content: str
    chunk_index: int
    similarity: float
    metadata: dict[str, Any] = Field(
        default_factory=dict
    )


class RAGRequest(BaseModel):
    """Incoming Harbor knowledge-base question."""

    question: str = Field(
        min_length=1,
        max_length=4000,
    )


class RAGResponse(BaseModel):
    """Final response returned by the RAG pipeline."""

    answer: str
    grounded: bool

    citations: list[Citation] = Field(
        default_factory=list
    )

    retrieved_chunks: int = 0