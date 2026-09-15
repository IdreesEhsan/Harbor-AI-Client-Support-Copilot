from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.rag import Citation


class AgentDecision(BaseModel):
    """
    Structured decision produced by Harbor's routing model.

    The router makes two separate decisions:

    1. action:
       What Harbor should do next.

    2. answer_source:
       Where Harbor should obtain information when the
       selected action is "answer".

    Keeping these decisions separate prevents conversation
    memory from being treated as authoritative KB evidence.
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
    Request accepted by Harbor's agent endpoint.
    """

    message: str = Field(
        min_length=1,
        max_length=4000,
    )

    conversation_id: str | None = None


class AgentResponse(BaseModel):
    """
    Response returned by Harbor's agent endpoint.

    answer_source remains an internal orchestration detail
    for now and is therefore not exposed through this model.
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

    citations: list[Citation] = Field(
        default_factory=list
    )

    escalation_required: bool = False

    # Returned so the frontend can continue the same
    # conversation.
    conversation_id: str | None = None