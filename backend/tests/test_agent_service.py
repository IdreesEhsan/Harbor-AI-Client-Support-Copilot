from unittest.mock import patch

import pytest

from app.agent.service import run_agent


@patch(
    "app.agent.service.harbor_graph"
)
def test_run_agent_answer(
    mock_graph,
):
    mock_graph.invoke.return_value = {
        "action": "answer",
        "severity": "low",
        "answer": "Refunds take 5 to 10 business days.",
        "citations": [
            {
                "source": "refund_policy.txt",
                "chunk_index": 0,
                "similarity": 0.91,
                "metadata": {},
            }
        ],
        "escalation_required": False,
    }

    result = run_agent(
        message="How long does a refund take?",
        user_id="user-123",
    )

    assert result.action == "answer"
    assert result.severity == "low"
    assert result.escalation_required is False


@patch(
    "app.agent.service.harbor_graph"
)
def test_run_agent_escalation(
    mock_graph,
):
    mock_graph.invoke.return_value = {
        "action": "escalate",
        "severity": "high",
        "answer": (
            "This request requires human support."
        ),
        "citations": [],
        "escalation_required": True,
    }

    result = run_agent(
        message="I need a human.",
        user_id="user-123",
    )

    assert result.action == "escalate"
    assert result.escalation_required is True


def test_run_agent_rejects_empty_message():
    with pytest.raises(ValueError):
        run_agent(
            message="   ",
            user_id="user-123",
        )


@patch(
    "app.agent.service.harbor_graph"
)
def test_run_agent_rejects_invalid_action(
    mock_graph,
):
    mock_graph.invoke.return_value = {
        "action": "unknown",
        "answer": "Something",
    }

    with pytest.raises(RuntimeError):
        run_agent(
            message="Hello",
            user_id="user-123",
        )