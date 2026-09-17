import re
from typing import Any

from app.agent.graph import (
    harbor_graph,
)

from app.agent.schemas import (
    AgentResponse,
)

from app.core.config import (
    get_settings,
)

from app.guardrails.execution_control import (
    ExecutionLimitExceededError,
)

from app.guardrails.output_guardrail import (
    evaluate_output,
)

from app.guardrails.pipeline import (
    run_input_guardrails,
)

from app.services.conversation_memory import (
    update_summary_memory,
)

from app.services.conversation_service import (
    finalize_conversation_turn,
    load_conversation_summary,
    load_recent_history,
    prepare_conversation,
    save_user_message,
)

from app.services.memory_service import (
    format_history,
)

from app.services.ticket_service import (
    prepare_support_ticket,
)


# ============================================================
# SAFE RESPONSES
# ============================================================

SAFE_OUTPUT_FALLBACK = (
    "I couldn't return that response safely. "
    "Please rephrase your support question or "
    "ask to speak with a human support agent."
)


SAFE_EXECUTION_LIMIT_FALLBACK = (
    "I couldn't complete this request safely within the "
    "allowed processing limits. Please try again or ask "
    "to speak with a human support agent."
)


TICKET_CONFIRMATION_PROMPT = (
    "This request requires review by a Harbor support agent. "
    "Would you like me to create a support ticket for you?"
)


TICKET_CREATED_RESPONSE = (
    "Your support ticket has been created successfully. "
    "A Harbor support agent can now review your request."
)


TICKET_CANCELLED_RESPONSE = (
    "No problem. I haven't created a support ticket. "
    "You can ask me to create one later if you need human support."
)


TICKET_CONFIRMATION_REMINDER = (
    "I haven't created a ticket yet. "
    "Please reply with yes or no to confirm whether you want "
    "me to create a support ticket."
)


CONFIRMATION_MARKER = (
    "Would you like me to create a support ticket"
)


# ============================================================
# ACTION ESCALATION PATTERNS
# ============================================================

ACTION_ESCALATION_PATTERNS = (
    r"\bi want (?:a|my)?\s*refund\b",
    r"\bi need (?:a|my)?\s*refund\b",
    r"\brefund (?:my|the|this)\b",
    r"\brefund me\b",
    r"\bplease refund\b",

    r"\bcharged twice\b",
    r"\bdouble charged\b",
    r"\bduplicate charge\b",
    r"\bcharged more than once\b",
    r"\bpayment dispute\b",
    r"\bdispute (?:this|the|a)?\s*charge\b",
    r"\bunauthorized charge\b",
    r"\bchargeback\b",

    r"\bcancel my subscription\b",
    r"\bcancel my order\b",
    r"\bcancel my account\b",
    r"\bplease cancel\b",
    r"\bi want to cancel\b",

    r"\bdelete my account\b",
    r"\bclose my account\b",
    r"\bterminate my account\b",

    r"\bi want (?:a|an)?\s*human\b",
    r"\bi need (?:a|an)?\s*human\b",
    r"\bhuman support\b",
    r"\bspeak (?:to|with) (?:a )?human\b",
    r"\bspeak (?:to|with) (?:an )?agent\b",
    r"\bsupport agent\b",
    r"\bcustomer service representative\b",
    r"\bescalate (?:this|my request|the issue)\b",
)


AFFIRMATIVE_RESPONSES = {
    "yes",
    "yes please",
    "yes, please",
    "yeah",
    "yep",
    "sure",
    "ok",
    "okay",
    "please do",
    "do it",
    "go ahead",
    "create it",
    "create the ticket",
    "create a ticket",
    "open it",
    "open the ticket",
}


NEGATIVE_RESPONSES = {
    "no",
    "no thanks",
    "no thank you",
    "not now",
    "don't",
    "dont",
    "do not",
    "cancel",
    "never mind",
    "nevermind",
    "stop",
}


# ============================================================
# CONFIRMATION HELPERS
# ============================================================

def normalize_confirmation_text(
    message: str,
) -> str:
    normalized = (
        message
        .strip()
        .lower()
    )

    normalized = re.sub(
        r"[.!?]+$",
        "",
        normalized,
    )

    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    )

    return normalized.strip()


def is_affirmative_response(
    message: str,
) -> bool:
    return (
        normalize_confirmation_text(
            message
        )
        in AFFIRMATIVE_RESPONSES
    )


def is_negative_response(
    message: str,
) -> bool:
    return (
        normalize_confirmation_text(
            message
        )
        in NEGATIVE_RESPONSES
    )


def requires_ticket_confirmation(
    message: str,
) -> bool:
    """
    Detect a support action rather than an informational
    question.
    """

    if not isinstance(
        message,
        str,
    ):
        return False

    normalized = (
        message
        .strip()
        .lower()
    )

    if not normalized:
        return False

    return any(
        re.search(
            pattern,
            normalized,
            flags=re.IGNORECASE,
        )
        for pattern
        in ACTION_ESCALATION_PATTERNS
    )


def has_pending_ticket_confirmation(
    recent_messages: list[dict[str, Any]],
) -> bool:
    """
    Search recent assistant history for an unresolved Harbor
    ticket-confirmation prompt.

    Do not return False merely because a later assistant
    reminder does not contain the original marker.
    """

    for item in reversed(
        recent_messages
    ):
        if (
            item.get("role")
            != "assistant"
        ):
            continue

        content = str(
            item.get(
                "content",
                "",
            )
        )

        if (
            CONFIRMATION_MARKER
            in content
        ):
            return True

    return False


def get_pending_escalation_message(
    recent_messages: list[dict[str, Any]],
) -> str | None:
    """
    Find the original customer request immediately preceding
    the ticket-confirmation prompt.
    """

    confirmation_index = None

    for index in range(
        len(recent_messages) - 1,
        -1,
        -1,
    ):
        history_message = (
            recent_messages[index]
        )

        if (
            history_message.get("role")
            != "assistant"
        ):
            continue

        content = str(
            history_message.get(
                "content",
                "",
            )
        )

        if (
            CONFIRMATION_MARKER
            in content
        ):
            confirmation_index = (
                index
            )
            break

    if confirmation_index is None:
        return None

    for index in range(
        confirmation_index - 1,
        -1,
        -1,
    ):
        history_message = (
            recent_messages[index]
        )

        if (
            history_message.get("role")
            != "user"
        ):
            continue

        content = str(
            history_message.get(
                "content",
                "",
            )
        ).strip()

        if content:
            return content

    return None


# ============================================================
# SEVERITY
# ============================================================

def normalize_severity(
    severity: str | None,
) -> str:
    allowed = {
        "low",
        "medium",
        "high",
        "critical",
    }

    if severity in allowed:
        return severity

    return "medium"


def determine_ticket_severity(
    message: str,
    graph_severity: str | None = None,
) -> str:
    severity = (
        normalize_severity(
            graph_severity
        )
    )

    normalized = (
        message.lower()
    )

    high_priority_patterns = (
        r"\bcharged twice\b",
        r"\bdouble charged\b",
        r"\bduplicate charge\b",
        r"\bunauthorized charge\b",
        r"\bpayment dispute\b",
        r"\bchargeback\b",
        r"\bfraud\b",
    )

    high_priority = any(
        re.search(
            pattern,
            normalized,
            flags=re.IGNORECASE,
        )
        for pattern
        in high_priority_patterns
    )

    if (
        high_priority
        and severity
        in {
            "low",
            "medium",
        }
    ):
        return "high"

    return severity


# ============================================================
# TICKET HELPERS
# ============================================================

def build_escalation_title(
    message: str,
) -> str:
    cleaned = (
        message.strip()
    )

    if not cleaned:
        return (
            "Customer support escalation"
        )

    max_length = 80

    if len(cleaned) <= max_length:
        return cleaned

    return (
        cleaned[
            : max_length - 3
        ].rstrip()
        + "..."
    )


def create_escalation_ticket(
    *,
    user_id: str,
    conversation_id: str,
    message: str,
    severity: str,
) -> dict:
    safe_severity = (
        normalize_severity(
            severity
        )
    )

    return (
        prepare_support_ticket(
            user_id=user_id,

            conversation_id=(
                conversation_id
            ),

            title=(
                build_escalation_title(
                    message
                )
            ),

            description=message,

            severity=safe_severity,
        )
    )


# ============================================================
# METADATA HELPERS
# ============================================================

def serialize_citations(
    citations: list[Any] | None,
) -> list[dict[str, Any]]:
    """
    Convert Pydantic Citation objects or dictionaries into
    JSON-compatible dictionaries before saving to Supabase.
    """

    serialized = []

    for citation in (
        citations or []
    ):
        if isinstance(
            citation,
            dict,
        ):
            serialized.append(
                citation
            )

        elif hasattr(
            citation,
            "model_dump",
        ):
            serialized.append(
                citation.model_dump()
            )

    return serialized


def build_message_metadata(
    *,
    action: str,
    severity: str,
    citations: list[Any] | None = None,
    escalation_required: bool = False,
    ticket_id: str | None = None,
    ticket_status: str | None = None,
    approval_status: str | None = None,
) -> dict[str, Any]:
    return {
        "action":
            action,

        "severity":
            severity,

        "citations":
            serialize_citations(
                citations
            ),

        "escalation_required":
            escalation_required,

        "ticket_id":
            ticket_id,

        "ticket_status":
            ticket_status,

        "approval_status":
            approval_status,
    }


# ============================================================
# SAFE CONVERSATION FINALIZATION
# ============================================================

def update_summary_safely(
    conversation_id: str,
) -> None:
    try:
        update_summary_memory(
            conversation_id
        )

    except Exception:
        pass


def finish_turn(
    *,
    conversation_id: str,
    answer: str,
    metadata: dict[str, Any],
) -> None:
    """
    Persist the complete reconstructable assistant turn.
    """

    finalize_conversation_turn(
        conversation_id=(
            conversation_id
        ),

        assistant_message=answer,

        metadata=metadata,
    )

    update_summary_safely(
        conversation_id
    )


# ============================================================
# MAIN AGENT
# ============================================================

def run_agent(
    message: str,
    user_id: str,
    conversation_id: str | None = None,
) -> AgentResponse:
    settings = get_settings()

    # ========================================================
    # 1. VALIDATE REQUEST
    # ========================================================

    if not isinstance(
        message,
        str,
    ):
        raise TypeError(
            "Message must be a string."
        )

    message = message.strip()

    if not message:
        raise ValueError(
            "Message cannot be empty."
        )

    # ========================================================
    # 2. INPUT GUARDRAILS
    # ========================================================

    guardrail_result = (
        run_input_guardrails(
            message
        )
    )

    if (
        guardrail_result.status
        == "redact"
    ):
        safe_message = (
            guardrail_result
            .redacted_content
            or message
        )

    else:
        safe_message = (
            message
        )

    # ========================================================
    # 3. CONVERSATION
    # ========================================================

    conversation = (
        prepare_conversation(
            user_id=user_id,
            conversation_id=(
                conversation_id
            ),
        )
    )

    active_conversation_id = str(
        conversation["id"]
    )

    # ========================================================
    # 4. LOAD MEMORY BEFORE CURRENT MESSAGE
    # ========================================================

    recent_messages = (
        load_recent_history(
            conversation_id=(
                active_conversation_id
            ),
            limit=(
                settings
                .memory_buffer_size
            ),
        )
    )

    history = (
        format_history(
            recent_messages
        )
    )

    conversation_summary = (
        load_conversation_summary(
            active_conversation_id
        )
    )

    # ========================================================
    # 5. CHECK PENDING TICKET CONFIRMATION
    # ========================================================

    pending_confirmation = (
        has_pending_ticket_confirmation(
            recent_messages
        )
    )

    pending_request = None

    if pending_confirmation:
        pending_request = (
            get_pending_escalation_message(
                recent_messages
            )
        )

    # ========================================================
    # 6. SAVE CURRENT CUSTOMER MESSAGE
    # ========================================================

    save_user_message(
        conversation_id=(
            active_conversation_id
        ),
        message=safe_message,
    )

    # ========================================================
    # 7. EXISTING TICKET CONFIRMATION
    # ========================================================

    if (
        pending_confirmation
        and pending_request
    ):
        # ----------------------------------------------------
        # YES
        # ----------------------------------------------------

        if (
            is_affirmative_response(
                safe_message
            )
        ):
            severity = (
                determine_ticket_severity(
                    pending_request,
                    "medium",
                )
            )

            ticket = (
                create_escalation_ticket(
                    user_id=user_id,

                    conversation_id=(
                        active_conversation_id
                    ),

                    message=(
                        pending_request
                    ),

                    severity=severity,
                )
            )

            answer = (
                f"{TICKET_CREATED_RESPONSE}\n\n"
                f"Ticket ID: {ticket['id']}\n"
                f"Status: "
                f"{ticket.get('status', 'pending_approval')}\n"
                f"Approval: "
                f"{ticket.get('approval_status', 'pending')}"
            )

            metadata = (
                build_message_metadata(
                    action="escalate",
                    severity=severity,
                    citations=[],
                    escalation_required=True,
                    ticket_id=str(
                        ticket["id"]
                    ),
                    ticket_status=(
                        ticket.get(
                            "status"
                        )
                    ),
                    approval_status=(
                        ticket.get(
                            "approval_status"
                        )
                    ),
                )
            )

            finish_turn(
                conversation_id=(
                    active_conversation_id
                ),
                answer=answer,
                metadata=metadata,
            )

            return AgentResponse(
                answer=answer,

                action="escalate",

                severity=severity,

                citations=[],

                escalation_required=True,

                conversation_id=(
                    active_conversation_id
                ),

                ticket_id=str(
                    ticket["id"]
                ),

                ticket_status=(
                    ticket.get(
                        "status"
                    )
                ),

                approval_status=(
                    ticket.get(
                        "approval_status"
                    )
                ),
            )

        # ----------------------------------------------------
        # NO
        # ----------------------------------------------------

        if (
            is_negative_response(
                safe_message
            )
        ):
            answer = (
                TICKET_CANCELLED_RESPONSE
            )

            metadata = (
                build_message_metadata(
                    action="answer",
                    severity="low",
                    citations=[],
                    escalation_required=False,
                )
            )

            finish_turn(
                conversation_id=(
                    active_conversation_id
                ),
                answer=answer,
                metadata=metadata,
            )

            return AgentResponse(
                answer=answer,

                action="answer",

                severity="low",

                citations=[],

                escalation_required=False,

                conversation_id=(
                    active_conversation_id
                ),

                ticket_id=None,

                ticket_status=None,

                approval_status=None,
            )

        # ----------------------------------------------------
        # UNCLEAR
        # ----------------------------------------------------

        severity = (
            determine_ticket_severity(
                pending_request,
                "medium",
            )
        )

        answer = (
            TICKET_CONFIRMATION_REMINDER
        )

        metadata = (
            build_message_metadata(
                action="clarify",
                severity=severity,
                citations=[],
                escalation_required=True,
            )
        )

        finish_turn(
            conversation_id=(
                active_conversation_id
            ),
            answer=answer,
            metadata=metadata,
        )

        return AgentResponse(
            answer=answer,

            action="clarify",

            severity=severity,

            citations=[],

            escalation_required=True,

            conversation_id=(
                active_conversation_id
            ),

            ticket_id=None,

            ticket_status=None,

            approval_status=None,
        )

    # ========================================================
    # 8. LANGGRAPH INPUT
    # ========================================================

    graph_question = (
        message
        if guardrail_result.status
        == "block"
        else safe_message
    )

    initial_state = {
        "question":
            graph_question,

        "user_id":
            user_id,

        "conversation_id":
            active_conversation_id,

        "history":
            history,

        "conversation_summary":
            conversation_summary
            or "",

        "step_count":
            0,

        "tool_call_count":
            0,

        "execution_limit_reached":
            False,
    }

    # ========================================================
    # 9. RUN LANGGRAPH
    # ========================================================

    try:
        result = (
            harbor_graph.invoke(
                initial_state
            )
        )

    except ExecutionLimitExceededError:
        result = {
            "answer":
                SAFE_EXECUTION_LIMIT_FALLBACK,

            "action":
                "escalate",

            "severity":
                "medium",

            "citations":
                [],

            "escalation_required":
                True,

            "execution_limit_reached":
                True,
        }

    # ========================================================
    # 10. VALIDATE RESULT
    # ========================================================

    action = (
        result.get(
            "action"
        )
    )

    if action not in {
        "answer",
        "clarify",
        "escalate",
    }:
        raise RuntimeError(
            "Harbor agent returned an invalid action."
        )

    raw_answer = (
        result.get(
            "answer"
        )
    )

    if (
        not isinstance(
            raw_answer,
            str,
        )
        or not raw_answer.strip()
    ):
        raise RuntimeError(
            "Harbor agent returned an invalid answer."
        )

    # ========================================================
    # 11. OUTPUT GUARDRAIL
    # ========================================================

    output_result = (
        evaluate_output(
            raw_answer
        )
    )

    if (
        output_result.status
        == "allow"
    ):
        safe_answer = (
            raw_answer
        )

    elif (
        output_result.status
        == "redact"
    ):
        safe_answer = (
            output_result
            .redacted_content
            or SAFE_OUTPUT_FALLBACK
        )

    else:
        safe_answer = (
            SAFE_OUTPUT_FALLBACK
        )

    if not safe_answer.strip():
        safe_answer = (
            SAFE_OUTPUT_FALLBACK
        )

    # ========================================================
    # 12. CONFIRMATION DECISION
    # ========================================================

    deterministic_action_request = (
        requires_ticket_confirmation(
            safe_message
        )
    )

    graph_requests_escalation = (
        action == "escalate"
        and bool(
            result.get(
                "escalation_required",
                False,
            )
        )
    )

    guardrail_requests_escalation = (
        guardrail_result.status
        == "escalate"
    )

    output_requests_escalation = (
        output_result.status
        == "escalate"
    )

    ticket_confirmation_required = (
        deterministic_action_request
        or graph_requests_escalation
        or guardrail_requests_escalation
        or output_requests_escalation
    )

    severity = (
        determine_ticket_severity(
            safe_message,

            result.get(
                "severity",
                "low",
            ),
        )
    )

    citations = (
        result.get(
            "citations",
            [],
        )
    )

    # ========================================================
    # 13. ASK FOR CONFIRMATION
    # ========================================================

    if ticket_confirmation_required:
        action = (
            "clarify"
        )

        safe_answer = (
            f"{safe_answer}\n\n"
            f"{TICKET_CONFIRMATION_PROMPT}"
        )

        metadata = (
            build_message_metadata(
                action=action,
                severity=severity,
                citations=citations,
                escalation_required=True,
            )
        )

        finish_turn(
            conversation_id=(
                active_conversation_id
            ),
            answer=safe_answer,
            metadata=metadata,
        )

        return AgentResponse(
            answer=safe_answer,

            action=action,

            severity=severity,

            citations=citations,

            escalation_required=True,

            conversation_id=(
                active_conversation_id
            ),

            ticket_id=None,

            ticket_status=None,

            approval_status=None,
        )

    # ========================================================
    # 14. NORMAL RESPONSE
    # ========================================================

    metadata = (
        build_message_metadata(
            action=action,
            severity=severity,
            citations=citations,
            escalation_required=False,
        )
    )

    finish_turn(
        conversation_id=(
            active_conversation_id
        ),
        answer=safe_answer,
        metadata=metadata,
    )

    return AgentResponse(
        answer=safe_answer,

        action=action,

        severity=severity,

        citations=citations,

        escalation_required=False,

        conversation_id=(
            active_conversation_id
        ),

        ticket_id=None,

        ticket_status=None,

        approval_status=None,
    )