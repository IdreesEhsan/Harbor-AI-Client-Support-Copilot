from app.agent.contextualizer import (
    contextualize_question,
)
from app.agent.router import (
    classify_request,
)
from app.agent.state import HarborAgentState
from app.agent.tools import (
    search_knowledge_base,
)
from app.agent.memory_answerer import (
    answer_from_memory,
)


def decision_node(
    state: HarborAgentState,
) -> dict:
    """
    Classify the current request and write the routing decision
    into LangGraph state.

    Both recent buffer memory and long-term summary memory help
    Harbor understand contextual follow-up requests.

    The router also determines which information source should
    handle an answer:
    - knowledge_base
    - conversation_memory
    """

    question = state.get(
        "question",
        "",
    ).strip()

    if not question:
        return {
            "error": "Question is missing.",
        }

    history = state.get(
        "history",
        [],
    )

    conversation_summary = state.get(
        "conversation_summary",
        "",
    )

    decision = classify_request(
        question,
        history=history,
        conversation_summary=conversation_summary,
    )

    return {
        "action": decision.action,

        # Keep answer source separate from action so Harbor can
        # distinguish workflow intent from information authority.
        "answer_source": decision.answer_source,

        "reason": decision.reason,
        "severity": decision.severity,
        "confidence": decision.confidence,
    }


def answer_node(
    state: HarborAgentState,
) -> dict:
    """
    Execute Harbor's grounded RAG pipeline.

    This node is specifically the knowledge-base answer path.

    Conversation memory helps contextualize the user's request,
    while the knowledge base remains the factual source used to
    generate the final grounded answer.

    Conversation memory must not be treated as authoritative
    knowledge-base evidence.
    """

    question = state.get(
        "question",
        "",
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

    history = state.get(
        "history",
        [],
    )

    conversation_summary = state.get(
        "conversation_summary",
        "",
    )

    # Rewrite contextual follow-ups into a standalone query
    # before searching the knowledge base.
    #
    # Memory is used here only to understand the question.
    # The retrieved KB chunks remain the factual authority.
    retrieval_question = contextualize_question(
        question=question,
        history=history,
        conversation_summary=conversation_summary,
    )

    result = search_knowledge_base.invoke(
        {
            "question": retrieval_question,
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

def memory_answer_node(
    state: HarborAgentState,
) -> dict:
    """
    Answer a request from Harbor's conversation memory.

    Unlike the RAG answer node, this node does not search the
    knowledge base. It may recall user-provided details from
    long-term summary memory or the recent conversation buffer.

    Because no knowledge-base evidence is used, this node returns
    no KB citations and is not marked as grounded RAG output.
    """

    question = state.get(
        "question",
        "",
    ).strip()

    if not question:
        return {
            "answer": (
                "I need a question before I can "
                "check the conversation history."
            ),
            "grounded": False,
            "citations": [],
            "retrieved_chunks": 0,
            "error": "Question is missing.",
        }

    history = state.get(
        "history",
        [],
    )

    conversation_summary = state.get(
        "conversation_summary",
        "",
    )

    answer = answer_from_memory(
        question=question,
        history=history,
        conversation_summary=conversation_summary,
    )

    return {
        "answer": answer,

        # "grounded" currently means grounded against the
        # authoritative Harbor knowledge base. Memory recall
        # therefore remains False.
        "grounded": False,

        # Conversation memory is not KB evidence, so do not
        # manufacture knowledge-base citations.
        "citations": [],
        "retrieved_chunks": 0,
        "escalation_required": False,
    }

def clarify_node(
    state: HarborAgentState,
) -> dict:
    """
    Ask for more information when the request is too
    ambiguous to handle safely.
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
    Mark the request for human support.

    A later Harbor phase will persist escalations and send
    them to systems such as Monday.com through automation.
    """

    reason = state.get(
        "reason",
        "Human review is required.",
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