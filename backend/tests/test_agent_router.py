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
    """
    A normal knowledge-base request should route
    to the answer branch and use the knowledge base.
    """

    client = MagicMock()

    client.chat.completions.create.return_value = (
        build_mock_response(
            {
                "action": "answer",
                "answer_source": "knowledge_base",
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
    assert decision.answer_source == "knowledge_base"
    assert decision.severity == "low"
    assert decision.confidence == 0.97


@patch(
    "app.agent.router.get_groq_client"
)
def test_router_returns_clarify(
    mock_get_client,
):
    """
    An ambiguous request should route to clarification.
    """

    client = MagicMock()

    client.chat.completions.create.return_value = (
        build_mock_response(
            {
                "action": "clarify",
                "answer_source": "knowledge_base",
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
    assert decision.severity == "low"


@patch(
    "app.agent.router.get_groq_client"
)
def test_router_returns_escalate(
    mock_get_client,
):
    """
    An explicit human-support request should route
    to escalation.
    """

    client = MagicMock()

    client.chat.completions.create.return_value = (
        build_mock_response(
            {
                "action": "escalate",
                "answer_source": "knowledge_base",
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
    assert decision.severity == "medium"


@patch(
    "app.agent.router.get_groq_client"
)
def test_router_uses_buffer_memory(
    mock_get_client,
):
    """
    Recent conversation history should be supplied to
    Groq when routing a contextual follow-up.
    """

    client = MagicMock()

    client.chat.completions.create.return_value = (
        build_mock_response(
            {
                "action": "answer",
                "answer_source": "knowledge_base",
                "reason": (
                    "Contextual refund follow-up."
                ),
                "severity": "low",
                "confidence": 0.96,
            }
        )
    )

    mock_get_client.return_value = client

    history = [
        {
            "role": "user",
            "content": (
                "How long does a refund take?"
            ),
        },
        {
            "role": "assistant",
            "content": (
                "Refunds take 5 to 10 "
                "business days."
            ),
        },
    ]

    decision = classify_request(
        "What if it takes longer than that?",
        history=history,
    )

    assert decision.action == "answer"
    assert decision.answer_source == "knowledge_base"

    call_kwargs = (
        client
        .chat
        .completions
        .create
        .call_args
        .kwargs
    )

    user_prompt = (
        call_kwargs["messages"][1]["content"]
    )

    assert (
        "RECENT CONVERSATION"
        in user_prompt
    )

    assert (
        "How long does a refund take?"
        in user_prompt
    )

    assert (
        "What if it takes longer than that?"
        in user_prompt
    )


@patch(
    "app.agent.router.get_groq_client"
)
def test_router_uses_summary_memory(
    mock_get_client,
):
    """
    Long-term summary memory should be supplied to Groq
    even when there is no recent buffer history.
    """

    client = MagicMock()

    client.chat.completions.create.return_value = (
        build_mock_response(
            {
                "action": "answer",
                "answer_source": "knowledge_base",
                "reason": (
                    "Follow-up about an unresolved refund."
                ),
                "severity": "medium",
                "confidence": 0.95,
            }
        )
    )

    mock_get_client.return_value = client

    summary = (
        "The user is waiting for refund REF-123. "
        "The refund was approved but has not arrived."
    )

    decision = classify_request(
        "What should I do now?",
        history=[],
        conversation_summary=summary,
    )

    assert decision.action == "answer"
    assert decision.answer_source == "knowledge_base"
    assert decision.severity == "medium"

    call_kwargs = (
        client
        .chat
        .completions
        .create
        .call_args
        .kwargs
    )

    user_prompt = (
        call_kwargs["messages"][1]["content"]
    )

    assert (
        "CONVERSATION SUMMARY"
        in user_prompt
    )

    assert summary in user_prompt

    assert (
        "What should I do now?"
        in user_prompt
    )


@patch(
    "app.agent.router.get_groq_client"
)
def test_router_uses_summary_and_buffer(
    mock_get_client,
):
    """
    Harbor should provide both long-term summary memory
    and recent buffer memory to the routing model.
    """

    client = MagicMock()

    client.chat.completions.create.return_value = (
        build_mock_response(
            {
                "action": "escalate",
                "answer_source": "knowledge_base",
                "reason": (
                    "The unresolved refund now requires "
                    "human support."
                ),
                "severity": "medium",
                "confidence": 0.98,
            }
        )
    )

    mock_get_client.return_value = client

    summary = (
        "The user is waiting for refund REF-123."
    )

    history = [
        {
            "role": "user",
            "content": (
                "I contacted my bank."
            ),
        },
        {
            "role": "assistant",
            "content": (
                "Does the bank show anything pending?"
            ),
        },
        {
            "role": "user",
            "content": "No.",
        },
    ]

    decision = classify_request(
        "Can I speak with someone about this?",
        history=history,
        conversation_summary=summary,
    )

    assert decision.action == "escalate"

    call_kwargs = (
        client
        .chat
        .completions
        .create
        .call_args
        .kwargs
    )

    user_prompt = (
        call_kwargs["messages"][1]["content"]
    )

    assert summary in user_prompt

    assert (
        "I contacted my bank."
        in user_prompt
    )

    assert (
        "Can I speak with someone about this?"
        in user_prompt
    )


@patch(
    "app.agent.router.get_groq_client"
)
def test_router_handles_no_memory(
    mock_get_client,
):
    """
    New conversations should explicitly represent the
    absence of both memory layers.
    """

    client = MagicMock()

    client.chat.completions.create.return_value = (
        build_mock_response(
            {
                "action": "answer",
                "answer_source": "knowledge_base",
                "reason": (
                    "Standalone knowledge-base question."
                ),
                "severity": "low",
                "confidence": 0.95,
            }
        )
    )

    mock_get_client.return_value = client

    decision = classify_request(
        "How do I reset my password?",
        history=[],
        conversation_summary=None,
    )

    assert decision.action == "answer"
    assert decision.answer_source == "knowledge_base"

    call_kwargs = (
        client
        .chat
        .completions
        .create
        .call_args
        .kwargs
    )

    user_prompt = (
        call_kwargs["messages"][1]["content"]
    )

    assert (
        "No previous conversation summary."
        in user_prompt
    )

    assert (
        "No previous conversation."
        in user_prompt
    )


@patch(
    "app.agent.router.get_groq_client"
)
def test_router_rejects_invalid_action(
    mock_get_client,
):
    """
    Unsupported routing actions should fail Pydantic
    validation and become AgentRoutingError.
    """

    client = MagicMock()

    client.chat.completions.create.return_value = (
        build_mock_response(
            {
                "action": "send_email",
                "answer_source": "knowledge_base",
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


@patch(
    "app.agent.router.get_groq_client"
)
def test_router_rejects_invalid_json(
    mock_get_client,
):
    """
    Malformed Groq output should become Harbor's
    routing-specific exception.
    """

    client = MagicMock()
    response = MagicMock()

    response.choices[0].message.content = (
        "not valid json"
    )

    client.chat.completions.create.return_value = (
        response
    )

    mock_get_client.return_value = client

    with pytest.raises(
        AgentRoutingError
    ):
        classify_request(
            "What is the refund policy?"
        )


def test_router_rejects_empty_message():
    """
    Blank input should be rejected before routing.
    """

    with pytest.raises(
        ValueError,
        match="Message cannot be empty",
    ):
        classify_request(
            "   "
        )


# ------------------------------------------------------------------
# Answer-source routing tests
# ------------------------------------------------------------------


@patch(
    "app.agent.router.get_groq_client"
)
def test_router_uses_knowledge_base_for_policy_question(
    mock_get_client,
):
    """
    Official Harbor policy questions must use the
    knowledge base as their authoritative source.
    """

    client = MagicMock()

    client.chat.completions.create.return_value = (
        build_mock_response(
            {
                "action": "answer",
                "answer_source": "knowledge_base",
                "reason": (
                    "The user is asking about "
                    "Harbor refund policy."
                ),
                "severity": "low",
                "confidence": 0.99,
            }
        )
    )

    mock_get_client.return_value = client

    decision = classify_request(
        "How long do Harbor refunds take?"
    )

    assert decision.action == "answer"
    assert (
        decision.answer_source
        == "knowledge_base"
    )


@patch(
    "app.agent.router.get_groq_client"
)
def test_router_uses_memory_for_order_reference(
    mock_get_client,
):
    """
    A request to recall a user-provided order reference
    must use conversation memory rather than RAG.
    """

    client = MagicMock()

    client.chat.completions.create.return_value = (
        build_mock_response(
            {
                "action": "answer",
                "answer_source": "conversation_memory",
                "reason": (
                    "The requested order reference was "
                    "provided earlier by the user."
                ),
                "severity": "low",
                "confidence": 0.99,
            }
        )
    )

    mock_get_client.return_value = client

    decision = classify_request(
        message="What was my order reference?",
        conversation_summary=(
            "The user's order reference is ORD-7842."
        ),
    )

    assert decision.action == "answer"
    assert (
        decision.answer_source
        == "conversation_memory"
    )


@patch(
    "app.agent.router.get_groq_client"
)
def test_router_uses_memory_for_refund_reason(
    mock_get_client,
):
    """
    User-provided details such as the reason for a refund
    belong to conversation memory.
    """

    client = MagicMock()

    client.chat.completions.create.return_value = (
        build_mock_response(
            {
                "action": "answer",
                "answer_source": "conversation_memory",
                "reason": (
                    "The user is asking Harbor to recall "
                    "a detail supplied earlier."
                ),
                "severity": "low",
                "confidence": 0.98,
            }
        )
    )

    mock_get_client.return_value = client

    decision = classify_request(
        message=(
            "What reason did I give for the refund?"
        ),
        history=[
            {
                "role": "user",
                "content": (
                    "The refund is for a damaged product."
                ),
            }
        ],
    )

    assert decision.action == "answer"
    assert (
        decision.answer_source
        == "conversation_memory"
    )


@patch(
    "app.agent.router.get_groq_client"
)
def test_router_keeps_contextual_policy_followup_on_kb(
    mock_get_client,
):
    """
    Conversation history may resolve a follow-up reference,
    but official policy answers must still come from the KB.
    """

    client = MagicMock()

    client.chat.completions.create.return_value = (
        build_mock_response(
            {
                "action": "answer",
                "answer_source": "knowledge_base",
                "reason": (
                    "Conversation history identifies the "
                    "refund topic, but the answer requires "
                    "official Harbor policy."
                ),
                "severity": "low",
                "confidence": 0.98,
            }
        )
    )

    mock_get_client.return_value = client

    decision = classify_request(
        message="What if it takes longer than that?",
        history=[
            {
                "role": "user",
                "content": (
                    "How long does a refund normally take?"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "Refunds normally take "
                    "5 to 10 business days."
                ),
            },
        ],
    )

    assert decision.action == "answer"
    assert (
        decision.answer_source
        == "knowledge_base"
    )