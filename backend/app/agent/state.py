from typing import Any, TypedDict


class HarborAgentState(TypedDict, total=False):
    """
    Shared state passed between Harbor's LangGraph nodes.

    Fields are optional because different nodes populate different
    parts of the state as the request moves through the graph.
    """

    # Request identity
    user_id: str
    conversation_id: str | None

    # Original user input
    question: str

    # Router output
    action: str
    reason: str
    severity: str
    confidence: float

    # RAG / answer output
    answer: str
    citations: list[dict[str, Any]]
    grounded: bool
    retrieved_chunks: int

    # Clarification flow
    clarification_question: str | None

    # Human escalation flow
    escalation_required: bool
    escalation_reason: str | None

    # Failure information used by graph nodes
    error: str | None