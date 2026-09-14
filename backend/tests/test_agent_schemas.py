import pytest
from pydantic import ValidationError

from app.agent.schemas import (
    AgentDecision,
    AgentRequest,
)


def test_valid_agent_decision():
    decision = AgentDecision(
        action="answer",
        reason=(
            "The question can be answered "
            "from the knowledge base."
        ),
        severity="low",
        confidence=0.95,
    )

    assert decision.action == "answer"
    assert decision.severity == "low"
    assert decision.confidence == 0.95


def test_invalid_agent_action():
    with pytest.raises(ValidationError):
        AgentDecision(
            action="unsupported_action",
            reason="Invalid routing action.",
            severity="low",
            confidence=0.50,
        )


def test_confidence_cannot_exceed_one():
    with pytest.raises(ValidationError):
        AgentDecision(
            action="answer",
            reason="Testing confidence validation.",
            severity="low",
            confidence=1.50,
        )


def test_empty_agent_request_is_invalid():
    with pytest.raises(ValidationError):
        AgentRequest(
            message=""
        )