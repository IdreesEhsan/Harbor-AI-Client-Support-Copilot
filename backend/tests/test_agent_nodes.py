from unittest.mock import patch

from app.agent.nodes import (
    answer_node,
    clarify_node,
    decision_node,
    escalation_node,
)
from app.agent.schemas import AgentDecision


@patch(
    "app.agent.nodes.classify_request"
)
def test_decision_node_routes_to_answer(
    mock_classify,
):
    mock_classify.return_value = (
        AgentDecision(
            action="answer",
            reason=(
                "Normal knowledge-base question."
            ),
            severity="low",
            confidence=0.97,
        )
    )

    result = decision_node(
        {
            "question": (
                "How long does a refund take?"
            )
        }
    )

    assert result["action"] == "answer"
    assert result["severity"] == "low"


@patch(
    "app.agent.nodes.search_knowledge_base"
)
def test_answer_node_returns_rag_result(
    mock_tool,
):
    mock_tool.invoke.return_value = {
        "answer": (
            "Refunds take 5 to 10 "
            "business days."
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

    result = answer_node(
        {
            "question": (
                "How long does a refund take?"
            )
        }
    )

    assert result["grounded"] is True
    assert result["retrieved_chunks"] == 1

    assert (
        result["answer"]
        == "Refunds take 5 to 10 business days."
    )


def test_clarify_node_requests_more_information():
    result = clarify_node(
        {
            "question": "It isn't working."
        }
    )

    assert (
        result["clarification_question"]
        is not None
    )

    assert result["grounded"] is False

    assert (
        result["escalation_required"]
        is False
    )


def test_escalation_node_marks_human_review():
    result = escalation_node(
        {
            "question": (
                "I need to speak to a human."
            ),
            "reason": (
                "User explicitly requested "
                "human support."
            ),
            "severity": "medium",
        }
    )

    assert (
        result["escalation_required"]
        is True
    )

    assert (
        result["escalation_reason"]
        == (
            "User explicitly requested "
            "human support."
        )
    )


def test_decision_node_handles_missing_question():
    result = decision_node(
        {}
    )

    assert (
        result["error"]
        == "Question is missing."
    )