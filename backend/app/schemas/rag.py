from typing import Any, Literal

from pydantic import (
    BaseModel,
    Field,
)


# ============================================================
# RAG
# ============================================================

class Citation(BaseModel):
    """
    Source evidence attached to a Harbor answer.
    """

    source: str

    chunk_index: int

    similarity: float

    metadata: dict[
        str,
        Any,
    ] = Field(
        default_factory=dict
    )


class RetrievedChunk(BaseModel):
    """
    Normalized representation of one retrieval result.
    """

    id: str

    document_id: str

    source_name: str

    content: str

    chunk_index: int

    similarity: float

    metadata: dict[
        str,
        Any,
    ] = Field(
        default_factory=dict
    )


class RAGRequest(BaseModel):
    """
    Incoming Harbor knowledge-base question.
    """

    question: str = Field(
        min_length=1,
        max_length=4000,
    )


class RAGResponse(BaseModel):
    """
    Final grounded Harbor response.
    """

    answer: str

    grounded: bool

    citations: list[
        Citation
    ] = Field(
        default_factory=list
    )

    retrieved_chunks: int = 0


# ============================================================
# FEEDBACK
# ============================================================

class RAGFeedbackRequest(BaseModel):
    """
    Feedback submitted against a RAG answer.
    """

    question: str = Field(
        min_length=1,
        max_length=4000,
    )

    answer: str = Field(
        min_length=1,
        max_length=10000,
    )

    rating: Literal[
        "positive",
        "negative",
    ]

    comment: str | None = Field(
        default=None,
        max_length=2000,
    )

    source_names: list[
        str
    ] = Field(
        default_factory=list
    )


class RAGFeedbackResponse(BaseModel):
    id: str

    rating: str

    message: str


# ============================================================
# EVALUATION CASES
# ============================================================

class RAGEvaluationCaseCreate(
    BaseModel
):
    question: str = Field(
        min_length=1,
        max_length=4000,
    )

    expected_answer_contains: list[
        str
    ] = Field(
        default_factory=list
    )

    expected_sources: list[
        str
    ] = Field(
        default_factory=list
    )

    expected_grounded: bool = True

    requester_role: Literal[
        "customer",
        "support_agent",
        "admin",
    ] = "customer"


class RAGEvaluationCaseRecord(
    RAGEvaluationCaseCreate
):
    id: str

    is_active: bool


class RAGEvaluationCaseResult(
    BaseModel
):
    case_id: str

    question: str

    actual_answer: str

    actual_grounded: bool

    actual_sources: list[
        str
    ]

    retrieved_chunks: int

    retrieval_pass: bool

    groundedness_pass: bool

    source_pass: bool

    answer_pass: bool

    overall_pass: bool


class RAGEvaluationRunResponse(
    BaseModel
):
    run_id: str

    total_cases: int

    passed_cases: int

    retrieval_hit_rate: float

    groundedness_accuracy: float

    source_accuracy: float

    answer_accuracy: float

    overall_pass_rate: float

    results: list[
        RAGEvaluationCaseResult
    ] = Field(
        default_factory=list
    )