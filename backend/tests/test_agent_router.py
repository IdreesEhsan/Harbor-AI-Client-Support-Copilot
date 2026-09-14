import json
from unittest.mock import MagicMock, patch

import pytest

from app.agent.router import (
    AgentRoutingError,
    classify_request,
)


def build_mock_response(
    payload: dict,
):
    """
    Create a minimal object matching the part of Groq's response
    structure used by Harbor's router.
    """

    response = MagicMock()

    response.choices[0].message.content = (
        json.dumps(payload)
    )

    return response


@patch(
    "app.agent.router.get_groq_client"
)
def test_router_returns_answer(
    mock_get_client,
):
    client = MagicMock()

    client.chat.completions.create.return_value = (
        build_mock_response(
            {
                "action": "answer",
                "reason": (
                    "Normal knowledge-base question."
                ),
                "severity": "low",
                "confidence": 0.97,
            }
        )
    )

    mock_get_client.return_value = client

    decision = classify_request(
        "What is the refund policy?"
    )

    assert decision.action == "answer"
    assert decision.severity == "low"


@patch(
    "app.agent.router.get_groq_client"
)
def test_router_returns_clarify(
    mock_get_client,
):
    client = MagicMock()

    client.chat.completions.create.return_value = (
        build_mock_response(
            {
                "action": "clarify",
                "reason": (
                    "The request is ambiguous."
                ),
                "severity": "low",
                "confidence": 0.92,
            }
        )
    )

    mock_get_client.return_value = client

    decision = classify_request(
        "It isn't working."
    )

    assert decision.action == "clarify"


@patch(
    "app.agent.router.get_groq_client"
)
def test_router_returns_escalate(
    mock_get_client,
):
    client = MagicMock()

    client.chat.completions.create.return_value = (
        build_mock_response(
            {
                "action": "escalate",
                "reason": (
                    "The user requested human support."
                ),
                "severity": "medium",
                "confidence": 0.99,
            }
        )
    )

    mock_get_client.return_value = client

    decision = classify_request(
        "Let me speak to a human."
    )

    assert decision.action == "escalate"


@patch(
    "app.agent.router.get_groq_client"
)
def test_router_rejects_invalid_action(
    mock_get_client,
):
    client = MagicMock()

    client.chat.completions.create.return_value = (
        build_mock_response(
            {
                "action": "send_email",
                "reason": "Invalid action.",
                "severity": "low",
                "confidence": 0.8,
            }
        )
    )

    mock_get_client.return_value = client

    with pytest.raises(
        AgentRoutingError
    ):
        classify_request(
            "Contact somebody."
        )


def test_router_rejects_empty_message():
    with pytest.raises(
        ValueError
    ):
        classify_request(
            "   "
        )