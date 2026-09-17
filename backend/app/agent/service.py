import re
from typing import Any

from app.agent.graph import harbor_graph
from app.agent.schemas import AgentResponse
from app.core.config import get_settings

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
# Safe responses
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
# Escalation intent rules
# ============================================================

ACTION_ESCALATION_PATTERNS = (
    # Refund actions
    r"\bi want (?:a|my)?\s*refund\b",
    r"\bi need (?:a|my)?\s*refund\b",
    r"\brefund (?:my|the|this)\b",
    r"\brefund me\b",
    r"\bplease refund\b",

    # Duplicate / disputed payments
    r"\bcharged twice\b",
    r"\bdouble charged\b",
    r"\bduplicate charge\b",
    r"\bcharged more than once\b",
    r"\bpayment dispute\b",
    r"\bdispute (?:this|the|a)?\s*charge\b",
    r"\bunauthorized charge\b",
    r"\bchargeback\b",

    # Cancellation actions
    r"\bcancel my subscription\b",
    r"\bcancel my order\b",
    r"\bcancel my account\b",
    r"\bplease cancel\b",
    r"\bi want to cancel\b",

    # Account-sensitive actions
    r"\bdelete my account\b",
    r"\bclose my account\b",
    r"\bterminate my account\b",

    # Explicit human support requests
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
# Confirmation helpers
# ============================================================

def normalize_confirmation_text(
    message: str,
) -> str:
    """
    Normalize a short yes/no confirmation reply.
    """

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
    """
    Return True when the customer clearly approves
    ticket creation.
    """

    normalized = (
        normalize_confirmation_text(
            message
        )
    )

    return (
        normalized
        in AFFIRMATIVE_RESPONSES
    )


def is_negative_response(
    message: str,
) -> bool:
    """
    Return True when the customer clearly declines
    ticket creation.
    """

    normalized = (
        normalize_confirmation_text(
            message
        )
    )

    return (
        normalized
        in NEGATIVE_RESPONSES
    )


def requires_ticket_confirmation(
    message: str,
) -> bool:
    """
    Detect requests that involve a real-world support action.

    General informational questions should not trigger this.

    Example:

        "What is your refund policy?"
            -> False

        "I was charged twice and want a refund."
            -> True
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
    Detect whether Harbor's most recent assistant message
    asked the customer to confirm ticket creation.
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

        return (
            CONFIRMATION_MARKER
            in content
        )

    return False


def get_pending_escalation_message(
    recent_messages: list[dict[str, Any]],
) -> str | None:
    """
    Recover the original customer request that caused Harbor
    to ask for ticket confirmation.

    Expected history:

        user:
            duplicate charge request

        assistant:
            ... Would you like me to create a support ticket?

        current user:
            yes

    The current "yes" is not yet included in recent_messages,
    so we can safely recover the previous customer request.
    """

    confirmation_index = None

    for index in range(
        len(recent_messages) - 1,
        -1,
        -1,
    ):
        message = (
            recent_messages[index]
        )

        if (
            message.get("role")
            != "assistant"
        ):
            continue

        content = str(
            message.get(
                "content",
                "",
            )
        )

        if (
            CONFIRMATION_MARKER
            in content
        ):
            confirmation_index = index
            break

    if confirmation_index is None:
        return None

    for index in range(
        confirmation_index - 1,
        -1,
        -1,
    ):
        message = (
            recent_messages[index]
        )

        if (
            message.get("role")
            != "user"
        ):
            continue

        content = str(
            message.get(
                "content",
                "",
            )
        ).strip()

        if content:
            return content

    return None


# ============================================================
# Severity
# ============================================================

def normalize_severity(
    severity: str | None,
) -> str:
    """
    Normalize model severity into Harbor's supported values.
    """

    allowed = {
        "low",
        "medium",
        "high",
        "critical",
    }

    if (
        severity
        in allowed
    ):
        return severity

    return "medium"


def determine_ticket_severity(
    message: str,
    graph_severity: str | None = None,
) -> str:
    """
    Apply a minimum severity for important payment issues.
    """

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
# Ticket helpers
# ============================================================

def build_escalation_title(
    message: str,
) -> str:
    """
    Build a deterministic ticket title from the customer's
    original request.
    """

    cleaned = (
        message.strip()
    )

    if not cleaned:
        return (
            "Customer support escalation"
        )

    max_length = 80

    if (
        len(cleaned)
        <= max_length
    ):
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
    """
    Create Harbor's internal pending-approval ticket.

    No Monday.com or n8n action occurs here.
    """

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
# Safe conversation persistence helpers
# ============================================================

def update_summary_safely(
    conversation_id: str,
) -> None:
    """
    Summary generation must never break the active support
    conversation.
    """

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
) -> None:
    """
    Persist Harbor's assistant response and update summary.
    """

    finalize_conversation_turn(
        conversation_id=(
            conversation_id
        ),

        assistant_message=answer,
    )

    update_summary_safely(
        conversation_id
    )


# ============================================================
# Main Harbor agent
# ============================================================

def run_agent(
    message: str,
    user_id: str,
    conversation_id: str | None = None,
) -> AgentResponse:
    """
    Execute one persistent Harbor support turn.

    Ticket flow:

        action request
            ↓
        explain / answer
            ↓
        ask customer confirmation
            ↓
        customer says yes
            ↓
        create support ticket
            ↓
        staff review
    """

    settings = get_settings()

    # ========================================================
    # 1. Validate request
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
    # 2. Input guardrails
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
        safe_message = message

    # ========================================================
    # 3. Prepare conversation
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
    # 4. Load existing memory BEFORE current message
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

    history = format_history(
        recent_messages
    )

    conversation_summary = (
        load_conversation_summary(
            active_conversation_id
        )
    )

    # ========================================================
    # 5. Check pending confirmation
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
    # 6. Persist current customer message
    # ========================================================

    save_user_message(
        conversation_id=(
            active_conversation_id
        ),
        message=safe_message,
    )

    # ========================================================
    # 7. Handle existing ticket confirmation
    # ========================================================

    if (
        pending_confirmation
        and pending_request
    ):
        # ----------------------------------------------------
        # Customer confirmed YES
        # ----------------------------------------------------

        if is_affirmative_response(
            safe_message
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
                f"Status: {ticket.get('status', 'pending_approval')}\n"
                f"Approval: {ticket.get('approval_status', 'pending')}"
            )

            finish_turn(
                conversation_id=(
                    active_conversation_id
                ),
                answer=answer,
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
        # Customer confirmed NO
        # ----------------------------------------------------

        if is_negative_response(
            safe_message
        ):
            answer = (
                TICKET_CANCELLED_RESPONSE
            )

            finish_turn(
                conversation_id=(
                    active_conversation_id
                ),
                answer=answer,
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
        # Customer gave unclear confirmation
        # ----------------------------------------------------

        answer = (
            TICKET_CONFIRMATION_REMINDER
        )

        finish_turn(
            conversation_id=(
                active_conversation_id
            ),
            answer=answer,
        )

        return AgentResponse(
            answer=answer,

            action="clarify",

            severity=(
                determine_ticket_severity(
                    pending_request,
                    "medium",
                )
            ),

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
    # 8. Prepare LangGraph state
    # ========================================================

    graph_question = (
        message
        if guardrail_result.status
        == "block"
        else safe_message
    )

    initial_state = {
        "question": graph_question,

        "user_id": user_id,

        "conversation_id": (
            active_conversation_id
        ),

        "history": history,

        "conversation_summary": (
            conversation_summary
            or ""
        ),

        "step_count": 0,

        "tool_call_count": 0,

        "execution_limit_reached": False,
    }

    # ========================================================
    # 9. Run LangGraph
    # ========================================================

    try:
        result = (
            harbor_graph.invoke(
                initial_state
            )
        )

    except ExecutionLimitExceededError:
        result = {
            "answer": (
                SAFE_EXECUTION_LIMIT_FALLBACK
            ),

            "action": "escalate",

            "severity": "medium",

            "citations": [],

            "escalation_required": True,

            "execution_limit_reached": True,
        }

    # ========================================================
    # 10. Validate graph contract
    # ========================================================

    action = result.get(
        "action"
    )

    if action not in {
        "answer",
        "clarify",
        "escalate",
    }:
        raise RuntimeError(
            "Harbor agent returned "
            "an invalid action."
        )

    raw_answer = result.get(
        "answer"
    )

    if not isinstance(
        raw_answer,
        str,
    ) or not raw_answer.strip():
        raise RuntimeError(
            "Harbor agent returned "
            "an invalid answer."
        )

    # ========================================================
    # 11. Output guardrail
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
        safe_answer = raw_answer

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
    # 12. Decide whether customer confirmation is required
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

    # ========================================================
    # 13. Ask for confirmation — DO NOT create ticket yet
    # ========================================================

    if ticket_confirmation_required:
        action = "clarify"

        safe_answer = (
            f"{safe_answer}\n\n"
            f"{TICKET_CONFIRMATION_PROMPT}"
        )

        finish_turn(
            conversation_id=(
                active_conversation_id
            ),
            answer=safe_answer,
        )

        return AgentResponse(
            answer=safe_answer,

            action=action,

            severity=severity,

            citations=result.get(
                "citations",
                [],
            ),

            escalation_required=True,

            conversation_id=(
                active_conversation_id
            ),

            ticket_id=None,

            ticket_status=None,

            approval_status=None,
        )

    # ========================================================
    # 14. Normal AI response
    # ========================================================

    finish_turn(
        conversation_id=(
            active_conversation_id
        ),
        answer=safe_answer,
    )

    return AgentResponse(
        answer=safe_answer,

        action=action,

        severity=severity,

        citations=result.get(
            "citations",
            [],
        ),

        escalation_required=False,

        conversation_id=(
            active_conversation_id
        ),

        ticket_id=None,

        ticket_status=None,

        approval_status=None,
    )