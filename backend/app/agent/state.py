from typing import TypedDict


class HarborAgentState(TypedDict, total=False):
    """
    Shared state passed between Harbor's LangGraph nodes.

    The state carries the current request, both conversation-memory
    layers, routing decisions, and the final response produced by
    the selected workflow branch.
    """

    user_id: str
    conversation_id: str

    # Current user request.
    question: str

    # Recent conversation turns used as short-term buffer memory.
    history: list[dict[str, str]]

    # Compressed long-term conversational memory.
    conversation_summary: str

    # Router decision.
    action: str

    # Determines which information source should be used when
    # action == "answer".
    #
    # Expected values:
    # - "knowledge_base"
    # - "conversation_memory"
    answer_source: str

    reason: str
    severity: str
    confidence: float

    # Final response data.
    answer: str
    citations: list[dict]
    grounded: bool
    retrieved_chunks: int

    # Clarification flow.
    clarification_question: str

    # Escalation flow.
    escalation_required: bool
    escalation_reason: str

    error: str