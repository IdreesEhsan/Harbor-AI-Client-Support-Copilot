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
from app.guardrails.pipeline import (
    run_input_guardrails,
)
from app.guardrails.tool_guardrail import (
    evaluate_tool_call,
)
from app.guardrails.execution_control import (
    ExecutionLimitExceededError,
    increment_tool_call_count,
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

    Conversation memory may contextualize the request, but
    Harbor's knowledge base remains the factual authority.

    Tool execution is protected by two independent controls:

    1. Request-scoped tool-call limits at the graph boundary.
    2. Tool authorization inside search_knowledge_base itself.
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

    # Convert a contextual follow-up into a standalone
    # retrieval question.
    #
    # Conversation memory helps Harbor understand the request,
    # but the knowledge base remains the factual authority.
    retrieval_question = contextualize_question(
        question=question,
        history=history,
        conversation_summary=conversation_summary,
    )

    current_tool_calls = state.get(
        "tool_call_count",
        0,
    )

    try:
        # Increment BEFORE execution.
        #
        # If Harbor has already consumed the maximum number
        # of tool calls, this raises before the protected
        # capability can execute.
        new_tool_call_count = (
            increment_tool_call_count(
                current_tool_calls
            )
        )

    except ExecutionLimitExceededError as exc:
        return {
            "answer": (
                "I couldn't continue processing this "
                "request safely because the tool execution "
                "limit was reached."
            ),
            "grounded": False,
            "citations": [],
            "retrieved_chunks": 0,

            # Preserve the previous valid count because the
            # rejected tool call never actually executed.
            "tool_call_count": current_tool_calls,
            "execution_limit_reached": True,
            "error": str(exc),
        }

    # The LangChain tool performs its own independent
    # authorization check before invoking the RAG service.
    #
    # This gives Harbor defense in depth:
    #
    # graph execution limit
    #       ↓
    # tool authorization
    #       ↓
    # actual RAG capability
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

        # Store the updated request-scoped execution count
        # back into LangGraph state.
        "tool_call_count": new_tool_call_count,
        "execution_limit_reached": False,
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

        # "grounded" means grounded against Harbor's
        # authoritative knowledge base. Conversation-memory
        # recall therefore remains False.
        "grounded": False,

        # Conversation memory is not KB evidence.
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

    Escalation means Harbor has determined that a human
    support agent should handle the case.

    This is different from human approval of a side-effecting
    tool. External escalation persistence will be implemented
    later.
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


def input_guardrail_node(
    state: HarborAgentState,
) -> dict:
    """
    Inspect user input before Harbor performs routing,
    retrieval, memory answering, or tool execution.

    If sensitive information can safely be removed, the
    sanitized message becomes the downstream question.
    """

    question = state.get(
        "question",
        "",
    )

    result = run_input_guardrails(
        question
    )

    update = {
        "original_question": question,
        "guardrail_status": result.status,
        "guardrail_category": result.category,
        "guardrail_reason": result.reason,
    }

    if result.status == "redact":
        update["question"] = (
            result.redacted_content
            or question
        )

    return update


def blocked_input_node(
    state: HarborAgentState,
) -> dict:
    """
    Return a controlled response for input rejected by
    Harbor's guardrails.

    This node does not call Groq, RAG, memory, or tools.
    """

    category = state.get(
        "guardrail_category",
        "policy_violation",
    )

    if category == "prompt_injection":
        answer = (
            "I can't follow instructions that attempt to "
            "override or expose Harbor's protected system "
            "instructions. I can still help with a normal "
            "support question."
        )
    else:
        answer = (
            "I couldn't process that request safely. "
            "Please rephrase your support question."
        )

    return {
        "answer": answer,

        # Internal graph provenance only.
        # This is not an LLM-selectable router value.
        "action": "answer",
        "answer_source": "guardrail",

        "severity": "low",
        "grounded": False,
        "citations": [],
        "retrieved_chunks": 0,
        "escalation_required": False,
    }


# ============================================================
# Tool Authorization
# ============================================================


def tool_authorization_node(
    state: HarborAgentState,
) -> dict:
    """
    Evaluate a requested tool before Harbor is allowed to
    execute it.

    This node performs authorization only. It deliberately
    does NOT execute the requested tool.

    Known read/analysis tools may be allowed, write tools
    require human approval, and unknown tools fail closed.
    """

    tool_name = state.get(
        "pending_tool_name",
        "",
    )

    result = evaluate_tool_call(
        tool_name
    )

    return {
        "tool_decision": result.decision,
        "tool_decision_reason": result.reason,
    }


# ============================================================
# Human-in-the-Loop Approval
# ============================================================


def pending_approval_node(
    state: HarborAgentState,
) -> dict:
    """
    Stop Harbor before a side-effecting operation executes.

    The requested tool and arguments remain represented in
    LangGraph state, but this node performs NO external
    operation.

    Future side-effecting capabilities such as ticket
    creation or external notifications must pass through
    human approval before execution.
    """

    tool_name = state.get(
        "pending_tool_name",
        "requested action",
    )

    return {
        "answer": (
            "This action requires human approval before "
            "Harbor can continue."
        ),

        # Human authorization is now required.
        "action": "escalate",

        # Internal provenance rather than an LLM-selectable
        # answer source.
        "answer_source": "guardrail",

        "severity": state.get(
            "severity",
            "medium",
        ),

        "grounded": False,
        "citations": [],
        "retrieved_chunks": 0,

        "escalation_required": True,

        "escalation_reason": (
            f"Tool '{tool_name}' requires human approval."
        ),

        # Crucially, the external operation has NOT happened.
        "pending_human_approval": True,
        "approval_status": "pending",
    }