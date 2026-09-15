from typing import TypedDict


class HarborAgentState(TypedDict, total=False):
    """
    Shared state passed between Harbor's LangGraph nodes.

    The state carries the current request, conversation
    memory, routing decisions, guardrail decisions,
    human-approval state, and the final response produced
    by the selected workflow branch.
    """

    user_id: str
    conversation_id: str

    # --------------------------------------------------------
    # Current request
    # --------------------------------------------------------

    question: str

    # Original request before sanitization.
    #
    # This field is ephemeral security state. It should not
    # be written to normal logs or persistent checkpoints
    # without sanitization.
    original_question: str

    # --------------------------------------------------------
    # Conversation memory
    # --------------------------------------------------------

    # Recent conversation turns used as short-term buffer
    # memory.
    history: list[dict[str, str]]

    # Compressed long-term conversational memory.
    conversation_summary: str

    # --------------------------------------------------------
    # Router decision
    # --------------------------------------------------------

    action: str

    # Determines which information source should be used when
    # action == "answer".
    #
    # Expected model-controlled values:
    # - "knowledge_base"
    # - "conversation_memory"
    answer_source: str

    reason: str
    severity: str
    confidence: float

    # --------------------------------------------------------
    # Final response
    # --------------------------------------------------------

    answer: str
    citations: list[dict]
    grounded: bool
    retrieved_chunks: int

    # --------------------------------------------------------
    # Clarification
    # --------------------------------------------------------

    clarification_question: str

    # --------------------------------------------------------
    # Escalation
    # --------------------------------------------------------

    escalation_required: bool
    escalation_reason: str

    # --------------------------------------------------------
    # Input guardrails
    # --------------------------------------------------------

    guardrail_status: str
    guardrail_category: str
    guardrail_reason: str

    # --------------------------------------------------------
    # Tool authorization
    # --------------------------------------------------------

    # Name of the side-effecting tool Harbor wants to run.
    pending_tool_name: str

    # Arguments intended for the pending tool.
    #
    # These arguments are kept separate from execution so
    # Harbor can inspect them before performing a write.
    pending_tool_args: dict

    # Tool-guardrail authorization decision.
    #
    # Expected values:
    # - "allow"
    # - "block"
    # - "require_approval"
    tool_decision: str

    # Human-readable reason for the tool decision.
    tool_decision_reason: str

    # --------------------------------------------------------
    # Human-in-the-loop approval
    # --------------------------------------------------------

    # True when Harbor has reached an operation that cannot
    # execute without explicit human authorization.
    pending_human_approval: bool

    # Current approval lifecycle state.
    #
    # Expected values:
    # - "not_required"
    # - "pending"
    # - "approved"
    # - "rejected"
    approval_status: str

    # --------------------------------------------------------
    # Execution safety
    # --------------------------------------------------------

    # Number of controlled graph/agent operations performed
    # during the current request.
    step_count: int

    # Number of tool executions performed during the current
    # request.
    tool_call_count: int

    # True when Harbor stopped processing because an
    # execution safety limit was reached.
    execution_limit_reached: bool

    # --------------------------------------------------------
    # Error handling
    # --------------------------------------------------------

    error: str