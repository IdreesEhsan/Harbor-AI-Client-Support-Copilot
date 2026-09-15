from langgraph.graph import END, START, StateGraph

from app.agent.nodes import (
    answer_node,
    clarify_node,
    decision_node,
    escalation_node,
    memory_answer_node,
)
from app.agent.state import HarborAgentState


def route_after_decision(
    state: HarborAgentState,
) -> str:
    """
    Select Harbor's next graph node from the validated
    routing decision.

    The action determines the workflow behavior, while
    answer_source determines which information source should
    handle normal answer requests.
    """

    action = state.get(
        "action"
    )

    answer_source = state.get(
        "answer_source",
        "knowledge_base",
    )

    if action == "answer":
        if answer_source == "knowledge_base":
            return "answer"

        if answer_source == "conversation_memory":
            return "memory_answer"

        # Never silently send an unsupported answer source
        # through the knowledge-base pipeline.
        raise ValueError(
            "Unsupported answer source: "
            f"{answer_source}"
        )

    if action == "clarify":
        return "clarify"

    if action == "escalate":
        return "escalate"

    # A missing or unsupported routing decision should never
    # silently continue through the graph.
    raise ValueError(
        f"Unsupported agent action: {action}"
    )


def build_harbor_graph():
    """
    Construct Harbor's LangGraph support workflow.

    Requests first pass through the decision node.

    Normal answer requests are then separated by information
    authority:

    - knowledge_base:
      Uses Harbor's grounded RAG pipeline.

    - conversation_memory:
      Uses previous conversation context without treating that
      information as authoritative knowledge-base evidence.

    Clarification and escalation remain separate controlled
    workflow branches.
    """

    graph = StateGraph(
        HarborAgentState
    )

    # ---------------------------------------------------------
    # Register graph nodes
    # ---------------------------------------------------------

    graph.add_node(
        "decision",
        decision_node,
    )

    # Authoritative Harbor knowledge-base / RAG answer.
    graph.add_node(
        "answer",
        answer_node,
    )

    # User-specific conversation-memory recall.
    graph.add_node(
        "memory_answer",
        memory_answer_node,
    )

    graph.add_node(
        "clarify",
        clarify_node,
    )

    graph.add_node(
        "escalate",
        escalation_node,
    )

    # ---------------------------------------------------------
    # Graph entry point
    # ---------------------------------------------------------

    graph.add_edge(
        START,
        "decision",
    )

    # ---------------------------------------------------------
    # Conditional routing
    # ---------------------------------------------------------

    graph.add_conditional_edges(
        "decision",
        route_after_decision,
        {
            "answer": "answer",
            "memory_answer": "memory_answer",
            "clarify": "clarify",
            "escalate": "escalate",
        },
    )

    # ---------------------------------------------------------
    # Terminal branches
    # ---------------------------------------------------------

    graph.add_edge(
        "answer",
        END,
    )

    graph.add_edge(
        "memory_answer",
        END,
    )

    graph.add_edge(
        "clarify",
        END,
    )

    graph.add_edge(
        "escalate",
        END,
    )

    return graph.compile()


harbor_graph = build_harbor_graph()