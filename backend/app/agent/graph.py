from langgraph.graph import END, START, StateGraph

from app.agent.nodes import (
    answer_node,
    clarify_node,
    decision_node,
    escalation_node,
)
from app.agent.state import HarborAgentState


def route_after_decision(
    state: HarborAgentState,
) -> str:
    """
    Return the graph route selected by Harbor's decision node.

    LangGraph uses this value to choose the next node.
    """

    action = state.get("action")

    if action == "answer":
        return "answer"

    if action == "clarify":
        return "clarify"

    if action == "escalate":
        return "escalate"

    # A missing or unsupported routing decision should never silently
    # continue through the graph.
    raise ValueError(
        f"Unsupported agent action: {action}"
    )


def build_harbor_graph():
    """
    Construct Harbor's Phase 7 LangGraph workflow.

    The graph first classifies the request and then follows exactly
    one controlled branch: answer, clarify, or escalate.
    """

    graph = StateGraph(
        HarborAgentState
    )

    # Register graph nodes.
    graph.add_node(
        "decision",
        decision_node,
    )

    graph.add_node(
        "answer",
        answer_node,
    )

    graph.add_node(
        "clarify",
        clarify_node,
    )

    graph.add_node(
        "escalate",
        escalation_node,
    )

    # Every request begins with classification.
    graph.add_edge(
        START,
        "decision",
    )

    # Choose one branch based on the validated router output.
    graph.add_conditional_edges(
        "decision",
        route_after_decision,
        {
            "answer": "answer",
            "clarify": "clarify",
            "escalate": "escalate",
        },
    )

    # Each Phase 7 branch finishes after producing its result.
    graph.add_edge(
        "answer",
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