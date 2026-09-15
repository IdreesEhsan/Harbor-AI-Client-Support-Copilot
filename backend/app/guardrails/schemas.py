from typing import Literal

from pydantic import BaseModel, Field


GuardrailStatus = Literal[
    "allow",
    "redact",
    "block",
    "escalate",
]


RiskLevel = Literal[
    "low",
    "medium",
    "high",
    "critical",
]


GuardrailCategory = Literal[
    "none",
    "pii",
    "credential",
    "prompt_injection",
    "unsafe_tool_request",
    "policy_violation",
]


class GuardrailResult(BaseModel):
    """
    Structured result produced by a Harbor guardrail.

    Guardrails should return structured decisions rather than
    simple booleans so LangGraph can make explicit routing
    decisions later.
    """

    status: GuardrailStatus = "allow"

    category: GuardrailCategory = "none"

    reason: str = Field(
        min_length=1,
        max_length=500,
    )

    risk_level: RiskLevel = "low"

    redacted_content: str | None = None


class InputGuardrailResult(GuardrailResult):
    """
    Result of evaluating user input before normal Harbor
    agent processing.

    original_length is useful for diagnostics without storing
    the original potentially sensitive input inside logs.
    """

    original_length: int = Field(
        ge=0,
    )


class OutputGuardrailResult(GuardrailResult):
    """
    Result of evaluating an assistant response before it is
    returned to the user.
    """

    output_length: int = Field(
        ge=0,
    )