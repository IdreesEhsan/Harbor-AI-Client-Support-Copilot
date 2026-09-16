from typing import Literal

from pydantic import (
    BaseModel,
    Field,
)

from app.schemas.rag import Citation


class AgentDecision(BaseModel):
    """
    Structured decision produced by Harbor's routing model.

    action:
        What Harbor should do next.

    answer_source:
        Which trusted information source should handle an
        answer request.
    """

    action: Literal[
        "answer",
        "clarify",
        "escalate",
    ]

    answer_source: Literal[
        "knowledge_base",
        "conversation_memory",
    ] = "knowledge_base"

    reason: str = Field(
        min_length=1,
        max_length=500,
    )

    severity: Literal[
        "low",
        "medium",
        "high",
        "critical",
    ] = "low"

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )


class AgentRequest(BaseModel):
    """
    Request accepted by Harbor's support-agent endpoint.
    """

    message: str = Field(
        min_length=1,
        max_length=4000,
    )

    conversation_id: (
        str | None
    ) = None


class AgentResponse(BaseModel):
    """
    Safe customer-facing response returned by Harbor.

    Ticket fields are populated only when Harbor has
    successfully persisted a real internal escalation ticket.
    """

    answer: str

    action: Literal[
        "answer",
        "clarify",
        "escalate",
    ]

    severity: Literal[
        "low",
        "medium",
        "high",
        "critical",
    ]

    citations: list[Citation] = (
        Field(
            default_factory=list
        )
    )

    escalation_required: (
        bool
    ) = False

    conversation_id: (
        str | None
    ) = None

    # --------------------------------------------------------
    # Escalation information
    # --------------------------------------------------------

    ticket_id: (
        str | None
    ) = None

    ticket_status: (
        str | None
    ) = None

    approval_status: (
        str | None
    ) = None