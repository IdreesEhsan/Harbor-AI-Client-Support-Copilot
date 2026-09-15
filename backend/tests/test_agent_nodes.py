from unittest.mock import MagicMock, patch

from app.agent.nodes import (
    answer_node,
    clarify_node,
    decision_node,
    escalation_node,
    memory_answer_node,
)
from app.agent.schemas import AgentDecision


@patch(
    "app.agent.nodes.classify_request"
)
def test_decision_node_routes_to_answer(
    mock_classify,
):
    """
    A normal request should store the router's answer
    decision in LangGraph state.
    """

    mock_classify.return_value = AgentDecision(
        action="answer",
        reason="Knowledge-base question.",
        severity="low",
        confidence=0.98,
    )

    state = {
        "question": "What is the refund policy?",
        "history": [],
        "conversation_summary": "",
    }

    result = decision_node(state)

    assert result["answer_source"] == "knowledge_base"
    assert result["action"] == "answer"
    assert result["severity"] == "low"
    assert result["confidence"] == 0.98

    mock_classify.assert_called_once_with(
        "What is the refund policy?",
        history=[],
        conversation_summary="",
    )


@patch(
    "app.agent.nodes.classify_request"
)
def test_decision_node_passes_both_memory_layers(
    mock_classify,
):
    """
    The decision node must pass both short-term buffer
    memory and long-term summary memory to the router.
    """

    mock_classify.return_value = AgentDecision(
        action="answer",
        reason="Contextual refund follow-up.",
        severity="medium",
        confidence=0.96,
    )

    history = [
        {
            "role": "user",
            "content": "I contacted my bank.",
        },
        {
            "role": "assistant",
            "content": (
                "Does the bank show anything pending?"
            ),
        },
    ]

    summary = (
        "The user is waiting for refund REF-123."
    )

    state = {
        "question": "What should I do now?",
        "history": history,
        "conversation_summary": summary,
    }

    result = decision_node(state)

    assert result["action"] == "answer"

    mock_classify.assert_called_once_with(
        "What should I do now?",
        history=history,
        conversation_summary=summary,
    )


@patch(
    "app.agent.nodes.search_knowledge_base"
)
@patch(
    "app.agent.nodes.contextualize_question"
)
def test_answer_node_returns_rag_result(
    mock_contextualize,
    mock_search,
):
    """
    A standalone request should be contextualized and then
    passed into Harbor's grounded RAG tool.
    """

    mock_contextualize.return_value = (
        "What is the refund policy?"
    )

    mock_search.invoke.return_value = {
        "answer": (
            "Refunds normally take 5 to 10 "
            "business days."
        ),
        "grounded": True,
        "citations": [
            {
                "source": "refund-policy.txt",
                "chunk_id": "chunk-1",
            }
        ],
        "retrieved_chunks": 2,
    }

    state = {
        "question": "What is the refund policy?",
        "history": [],
        "conversation_summary": "",
    }

    result = answer_node(state)

    assert result["grounded"] is True
    assert result["retrieved_chunks"] == 2

    assert (
        "Refunds normally take"
        in result["answer"]
    )

    mock_contextualize.assert_called_once_with(
        question="What is the refund policy?",
        history=[],
        conversation_summary="",
    )

    mock_search.invoke.assert_called_once_with(
        {
            "question": (
                "What is the refund policy?"
            )
        }
    )


@patch(
    "app.agent.nodes.search_knowledge_base"
)
@patch(
    "app.agent.nodes.contextualize_question"
)
def test_answer_node_uses_buffer_memory(
    mock_contextualize,
    mock_search,
):
    """
    Recent history should reach the contextualizer before
    retrieval occurs.
    """

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
                "Refunds normally take 5 to 10 "
                "business days."
            ),
        },
    ]

    mock_contextualize.return_value = (
        "What should a customer do if a refund "
        "takes longer than 10 business days?"
    )

    mock_search.invoke.return_value = {
        "answer": (
            "Contact support if the refund exceeds "
            "the expected processing period."
        ),
        "grounded": True,
        "citations": [],
        "retrieved_chunks": 1,
    }

    state = {
        "question": (
            "What if it takes longer than that?"
        ),
        "history": history,
        "conversation_summary": "",
    }

    result = answer_node(state)

    assert result["grounded"] is True

    mock_contextualize.assert_called_once_with(
        question=(
            "What if it takes longer than that?"
        ),
        history=history,
        conversation_summary="",
    )

    mock_search.invoke.assert_called_once_with(
        {
            "question": (
                "What should a customer do if a "
                "refund takes longer than 10 "
                "business days?"
            )
        }
    )


@patch(
    "app.agent.nodes.search_knowledge_base"
)
@patch(
    "app.agent.nodes.contextualize_question"
)
def test_answer_node_uses_summary_memory(
    mock_contextualize,
    mock_search,
):
    """
    Persistent summary memory must reach the contextualizer
    before Harbor performs knowledge-base retrieval.
    """

    summary = (
        "The user is waiting for refund REF-123. "
        "The refund has already been approved."
    )

    mock_contextualize.return_value = (
        "What should the user do about delayed "
        "refund REF-123?"
    )

    mock_search.invoke.return_value = {
        "answer": (
            "The customer should contact support "
            "for further investigation."
        ),
        "grounded": True,
        "citations": [],
        "retrieved_chunks": 1,
    }

    state = {
        "question": "What should I do now?",
        "history": [],
        "conversation_summary": summary,
    }

    result = answer_node(state)

    assert result["grounded"] is True

    mock_contextualize.assert_called_once_with(
        question="What should I do now?",
        history=[],
        conversation_summary=summary,
    )

    mock_search.invoke.assert_called_once_with(
        {
            "question": (
                "What should the user do about "
                "delayed refund REF-123?"
            )
        }
    )


@patch(
    "app.agent.nodes.search_knowledge_base"
)
@patch(
    "app.agent.nodes.contextualize_question"
)
def test_answer_node_uses_summary_and_buffer(
    mock_contextualize,
    mock_search,
):
    """
    Both memory layers should be supplied to the
    contextualizer for long-running conversations.
    """

    summary = (
        "The user is waiting for refund REF-123."
    )

    history = [
        {
            "role": "user",
            "content": "I contacted my bank.",
        },
        {
            "role": "assistant",
            "content": (
                "Does the bank show a pending transaction?"
            ),
        },
        {
            "role": "user",
            "content": "No.",
        },
    ]

    mock_contextualize.return_value = (
        "What should the user do after their bank "
        "reported no pending transaction for "
        "refund REF-123?"
    )

    mock_search.invoke.return_value = {
        "answer": (
            "The customer should contact support."
        ),
        "grounded": True,
        "citations": [],
        "retrieved_chunks": 1,
    }

    state = {
        "question": "What should I do now?",
        "history": history,
        "conversation_summary": summary,
    }

    result = answer_node(state)

    assert result["grounded"] is True

    mock_contextualize.assert_called_once_with(
        question="What should I do now?",
        history=history,
        conversation_summary=summary,
    )


def test_clarify_node_requests_more_information():
    """
    Clarification should produce a safe response without
    calling the knowledge base.
    """

    state = {
        "question": "It isn't working.",
    }

    result = clarify_node(state)

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
    """
    Escalation should preserve the routing reason and mark
    the request for future human-support processing.
    """

    state = {
        "question": (
            "I need to speak with someone."
        ),
        "reason": (
            "The user requested human support."
        ),
    }

    result = escalation_node(state)

    assert (
        result["escalation_required"]
        is True
    )

    assert (
        result["escalation_reason"]
        == "The user requested human support."
    )

    assert result["grounded"] is False


def test_decision_node_handles_missing_question():
    """
    A missing question should fail safely before routing.
    """

    result = decision_node(
        {
            "question": "",
            "history": [],
            "conversation_summary": "",
        }
    )

    assert (
        result["error"]
        == "Question is missing."
    )


def test_answer_node_handles_missing_question():
    """
    A missing question should not trigger contextualization
    or RAG retrieval.
    """

    result = answer_node(
        {
            "question": "",
            "history": [],
            "conversation_summary": "",
        }
    )

    assert result["grounded"] is False
    assert result["citations"] == []
    assert result["retrieved_chunks"] == 0
    assert result["error"] == "Question is missing."

@patch(
    "app.agent.nodes.answer_from_memory"
)
def test_memory_answer_node_uses_conversation_memory(
    mock_answer_from_memory,
):
    """
    The memory-answer node should use conversation memory
    without searching Harbor's knowledge base.
    """

    mock_answer_from_memory.return_value = (
        "Your order reference was ORD-7842."
    )

    state = {
        "question": (
            "What was my order reference?"
        ),
        "history": [
            {
                "role": "user",
                "content": (
                    "Support asked me to wait "
                    "another two business days."
                ),
            }
        ],
        "conversation_summary": (
            "The user previously provided order "
            "reference ORD-7842."
        ),
    }

    result = memory_answer_node(
        state
    )

    assert result["answer"] == (
        "Your order reference was ORD-7842."
    )

    assert result["grounded"] is False
    assert result["citations"] == []
    assert result["retrieved_chunks"] == 0
    assert (
        result["escalation_required"]
        is False
    )

    mock_answer_from_memory.assert_called_once_with(
        question=(
            "What was my order reference?"
        ),
        history=state["history"],
        conversation_summary=(
            state["conversation_summary"]
        ),
    )


@patch(
    "app.agent.nodes.answer_from_memory"
)
def test_memory_answer_node_uses_summary_memory(
    mock_answer_from_memory,
):
    """
    Long-term summary memory should be passed to the
    memory-answer component.
    """

    mock_answer_from_memory.return_value = (
        "Your order reference was ORD-7842."
    )

    state = {
        "question": (
            "Remind me what my order reference was."
        ),
        "history": [],
        "conversation_summary": (
            "The user's order reference is ORD-7842."
        ),
    }

    result = memory_answer_node(
        state
    )

    assert "ORD-7842" in result["answer"]

    mock_answer_from_memory.assert_called_once_with(
        question=(
            "Remind me what my order reference was."
        ),
        history=[],
        conversation_summary=(
            "The user's order reference is ORD-7842."
        ),
    )


@patch(
    "app.agent.nodes.answer_from_memory"
)
def test_memory_answer_node_handles_missing_question(
    mock_answer_from_memory,
):
    """
    Missing questions should fail locally without
    making a Groq memory-answer call.
    """

    result = memory_answer_node(
        {
            "question": "   ",
            "history": [],
            "conversation_summary": "",
        }
    )

    assert result["grounded"] is False
    assert result["citations"] == []
    assert result["retrieved_chunks"] == 0

    assert (
        result["error"]
        == "Question is missing."
    )

    mock_answer_from_memory.assert_not_called()