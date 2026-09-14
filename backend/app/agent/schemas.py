from typing import Literal

from pydantic import BaseModel, Field


class AgentDecision(BaseModel):
    """
    Structured decision produced by Harbor's routing model.

    Restricting the action to known values prevents the LLM from
    inventing unsupported workflow destinations.
    """

    action: Literal[
        "answer",
        "clarify",
        "escalate",
    ]

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
    Request accepted by Harbor's future agent endpoint.
    """

    message: str = Field(
        min_length=1,
        max_length=4000,
    )

    conversation_id: str | None = None


class AgentResponse(BaseModel):
    """
    Final public response returned after LangGraph completes.
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

    citations: list[dict] = Field(
        default_factory=list
    )

    escalation_required: bool = False