from unittest.mock import patch

import pytest

from app.agent.graph import (
    harbor_graph,
    route_after_decision,
)
from app.agent.schemas import AgentDecision


def test_route_after_decision_answer():
    route = route_after_decision(
        {
            "action": "answer"
        }
    )

    assert route == "answer"


def test_route_after_decision_clarify():
    route = route_after_decision(
        {
            "action": "clarify"
        }
    )

    assert route == "clarify"


def test_route_after_decision_escalate():
    route = route_after_decision(
        {
            "action": "escalate"
        }
    )

    assert route == "escalate"


def test_route_after_decision_rejects_unknown_action():
    with pytest.raises(ValueError):
        route_after_decision(
            {
                "action": "unknown"
            }
        )


@patch(
    "app.agent.nodes.classify_request"
)
@patch(
    "app.agent.nodes.search_knowledge_base"
)
def test_graph_answer_path(
    mock_search_tool,
    mock_classify,
):
    mock_classify.return_value = (
        AgentDecision(
            action="answer",
            reason="Normal KB question.",
            severity="low",
            confidence=0.98,
        )
    )

    mock_search_tool.invoke.return_value = {
        "answer": (
            "Refunds take 5 to 10 business days."
        ),
        "grounded": True,
        "citations": [
            {
                "source": "refund_policy.txt",
                "chunk_index": 0,
                "similarity": 0.91,
                "metadata": {},
            }
        ],
        "retrieved_chunks": 1,
    }

    result = harbor_graph.invoke(
        {
            "question": (
                "How long does a refund take?"
            )
        }
    )

    assert result["action"] == "answer"
    assert result["grounded"] is True
    assert result["retrieved_chunks"] == 1

    assert (
        result["answer"]
        == "Refunds take 5 to 10 business days."
    )


@patch(
    "app.agent.nodes.classify_request"
)
def test_graph_clarify_path(
    mock_classify,
):
    mock_classify.return_value = (
        AgentDecision(
            action="clarify",
            reason="The request is ambiguous.",
            severity="low",
            confidence=0.91,
        )
    )

    result = harbor_graph.invoke(
        {
            "question": "It is not working."
        }
    )

    assert result["action"] == "clarify"
    assert result["grounded"] is False

    assert (
        result["clarification_question"]
        is not None
    )

    assert (
        result["escalation_required"]
        is False
    )


@patch(
    "app.agent.nodes.classify_request"
)
def test_graph_escalation_path(
    mock_classify,
):
    mock_classify.return_value = (
        AgentDecision(
            action="escalate",
            reason=(
                "User explicitly requested "
                "human support."
            ),
            severity="medium",
            confidence=0.99,
        )
    )

    result = harbor_graph.invoke(
        {
            "question": (
                "I want to speak to a human."
            )
        }
    )

    assert result["action"] == "escalate"

    assert (
        result["escalation_required"]
        is True
    )

    assert (
        result["severity"]
        == "medium"
    )