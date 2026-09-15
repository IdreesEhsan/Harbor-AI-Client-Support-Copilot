from langgraph.graph import END, START, StateGraph

from app.agent.execution import controlled_node
from app.agent.nodes import (
    answer_node,
    blocked_input_node,
    clarify_node,
    decision_node,
    escalation_node,
    input_guardrail_node,
    memory_answer_node,
)
from app.agent.state import HarborAgentState


def route_after_guardrail(
    state: HarborAgentState,
) -> str:
    """
    Decide whether the request may enter Harbor's normal
    agent workflow after input safety checks.

    Safe and sanitized requests continue to the decision
    router. Blocked requests receive a controlled response,
    while requests requiring human review go directly to the
    escalation branch.
    """

    status = state.get(
        "guardrail_status",
        "allow",
    )

    if status in {
        "allow",
        "redact",
    }:
        return "decision"

    if status == "block":
        return "blocked"

    if status == "escalate":
        return "escalate"

    # Fail closed instead of silently allowing an unknown
    # guardrail status into the normal agent workflow.
    raise ValueError(
        f"Unsupported guardrail status: {status}"
    )


def route_after_decision(
    state: HarborAgentState,
) -> str:
    """
    Select Harbor's next graph node from the validated
    routing decision.

    The action determines workflow behavior, while
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

    Every executable graph node is wrapped by
    controlled_node(). This provides centralized,
    request-scoped graph-step enforcement.

    Every request first passes through the input guardrail.

    Safe requests continue into Harbor's normal routing
    workflow. Sensitive-but-processable input may be
    sanitized before routing. Prompt-injection or other
    blocked input terminates through a controlled response.

    Normal answer requests are separated by information
    authority:

    - knowledge_base:
      Uses Harbor's grounded RAG pipeline.

    - conversation_memory:
      Uses previous conversation context without treating
      that information as authoritative KB evidence.

    Clarification and escalation remain separate controlled
    workflow branches.

    Execution counting happens before each node executes.
    If the configured graph-step limit would be exceeded,
    the protected node never runs.
    """

    graph = StateGraph(
        HarborAgentState
    )

    # ---------------------------------------------------------
    # Register guardrail nodes
    # ---------------------------------------------------------

    # Every incoming request first consumes one controlled
    # graph step while performing input safety checks.
    graph.add_node(
        "input_guardrail",
        controlled_node(
            input_guardrail_node
        ),
    )

    # Blocked input still passes through a controlled node.
    # This means even deterministic safety branches count as
    # real graph execution.
    graph.add_node(
        "blocked",
        controlled_node(
            blocked_input_node
        ),
    )

    # ---------------------------------------------------------
    # Register normal agent nodes
    # ---------------------------------------------------------

    # Routing/classification is a real agent operation and
    # therefore consumes one graph step.
    graph.add_node(
        "decision",
        controlled_node(
            decision_node
        ),
    )

    # Authoritative Harbor knowledge-base / RAG answer.
    #
    # answer_node has an additional tool-call limit, giving
    # this path two independent execution protections:
    #
    # graph step limit
    #       ↓
    # answer node
    #       ↓
    # tool-call limit
    #       ↓
    # tool authorization
    #       ↓
    # RAG
    graph.add_node(
        "answer",
        controlled_node(
            answer_node
        ),
    )

    # User-specific conversation-memory recall.
    graph.add_node(
        "memory_answer",
        controlled_node(
            memory_answer_node
        ),
    )

    graph.add_node(
        "clarify",
        controlled_node(
            clarify_node
        ),
    )

    graph.add_node(
        "escalate",
        controlled_node(
            escalation_node
        ),
    )

    # ---------------------------------------------------------
    # Graph entry point
    # ---------------------------------------------------------

    # Requests always enter through Harbor's protected input
    # guardrail rather than directly reaching the LLM router.
    graph.add_edge(
        START,
        "input_guardrail",
    )

    # ---------------------------------------------------------
    # Guardrail routing
    # ---------------------------------------------------------

    graph.add_conditional_edges(
        "input_guardrail",
        route_after_guardrail,
        {
            "decision": "decision",
            "blocked": "blocked",
            "escalate": "escalate",
        },
    )

    # ---------------------------------------------------------
    # Agent decision routing
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

    # A blocked request ends immediately. It must never
    # continue to the decision router, Groq, RAG, memory,
    # or tool execution.
    graph.add_edge(
        "blocked",
        END,
    )

    return graph.compile()


harbor_graph = build_harbor_graph()