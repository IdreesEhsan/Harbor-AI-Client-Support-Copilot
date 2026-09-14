from app.agent.router import classify_request
from app.agent.state import HarborAgentState
from app.agent.tools import search_knowledge_base


def decision_node(
    state: HarborAgentState,
) -> dict:
    """
    Classify the current request and write the routing decision
    into LangGraph state.

    This node decides what Harbor should do, but does not execute
    the selected action itself.
    """

    question = state.get(
        "question",
        ""
    ).strip()

    if not question:
        return {
            "error": "Question is missing.",
        }

    decision = classify_request(
        question
    )

    return {
        "action": decision.action,
        "reason": decision.reason,
        "severity": decision.severity,
        "confidence": decision.confidence,
    }


def answer_node(
    state: HarborAgentState,
) -> dict:
    """
    Execute Harbor's existing Phase 6 RAG pipeline.

    The LangGraph layer delegates knowledge retrieval and grounded
    generation to the already-tested RAG service.
    """

    question = state.get(
        "question",
        ""
    ).strip()

    if not question:
        return {
            "answer": (
                "I need a question before I can "
                "search the knowledge base."
            ),
            "grounded": False,
            "citations": [],
            "retrieved_chunks": 0,
            "error": "Question is missing.",
        }

    result = search_knowledge_base.invoke(
        {
            "question": question,
        }
    )

    return {
        "answer": result["answer"],
        "grounded": result["grounded"],
        "citations": result["citations"],
        "retrieved_chunks": result[
            "retrieved_chunks"
        ],
    }


def clarify_node(
    state: HarborAgentState,
) -> dict:
    """
    Ask the user for more information when the router determines
    that the original request is too ambiguous to handle safely.
    """

    clarification = (
        "Could you provide a little more detail "
        "about the issue you're experiencing?"
    )

    return {
        "answer": clarification,
        "clarification_question": clarification,
        "grounded": False,
        "citations": [],
        "retrieved_chunks": 0,
        "escalation_required": False,
    }


def escalation_node(
    state: HarborAgentState,
) -> dict:
    """
    Mark a request for human support.

    Phase 7 records the escalation decision in graph state.
    A later phase will persist escalations and send them to systems
    such as Monday.com through the automation workflow.
    """

    reason = state.get(
        "reason",
        "Human review is required."
    )

    return {
        "answer": (
            "This request requires human support. "
            "I'll mark it for escalation."
        ),
        "grounded": False,
        "citations": [],
        "retrieved_chunks": 0,
        "escalation_required": True,
        "escalation_reason": reason,
    }