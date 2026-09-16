from app.agent.graph import harbor_graph

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


def build_escalation_title(
    message: str,
) -> str:
    """
    Build a short deterministic escalation title.

    LLM output is deliberately not used in the ticket title,
    keeping ticket identity predictable.
    """

    cleaned_message = (
        message.strip()
    )

    if not cleaned_message:
        return (
            "Customer support escalation"
        )

    max_length = 80

    if (
        len(cleaned_message)
        <= max_length
    ):
        return cleaned_message

    return (
        cleaned_message[
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
    Persist Harbor's internal pending-approval ticket.

    This function does NOT:

    - approve the ticket;
    - call Monday.com;
    - call n8n;
    - send notifications.

    External operations remain behind Harbor's human approval
    and controlled execution workflow.
    """

    allowed_severities = {
        "low",
        "medium",
        "high",
        "critical",
    }

    safe_severity = (
        severity
        if severity
        in allowed_severities
        else "medium"
    )

    title = (
        build_escalation_title(
            message
        )
    )

    return (
        prepare_support_ticket(
            user_id=user_id,
            conversation_id=(
                conversation_id
            ),
            title=title,
            description=message,
            severity=safe_severity,
        )
    )


def run_agent(
    message: str,
    user_id: str,
    conversation_id: str | None = None,
) -> AgentResponse:
    """
    Execute one persistent Harbor conversation turn.

    Flow:

        request validation
                ↓
        input guardrail
                ↓
        conversation
                ↓
        memory
                ↓
        safe persistence
                ↓
        LangGraph
                ↓
        output guardrail
                ↓
        escalation ticket if required
                ↓
        safe assistant persistence
                ↓
        summary memory
                ↓
        customer response
    """

    settings = get_settings()

    # ========================================================
    # 1. Request validation
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
    # 2. Input guardrail
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
    # 4. Load memory
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
    # 5. Persist safe customer message
    # ========================================================

    save_user_message(
        conversation_id=(
            active_conversation_id
        ),
        message=safe_message,
    )

    # ========================================================
    # 6. Prepare graph input
    # ========================================================

    if (
        guardrail_result.status
        == "block"
    ):
        graph_question = message
    else:
        graph_question = (
            safe_message
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

        "execution_limit_reached": (
            False
        ),
    }

    # ========================================================
    # 7. Run protected LangGraph workflow
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

            "escalation_required": (
                True
            ),

            "execution_limit_reached": (
                True
            ),
        }

    # ========================================================
    # 8. Validate graph contract
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

    if not raw_answer:
        raise RuntimeError(
            "Harbor agent returned "
            "no answer."
        )

    if not isinstance(
        raw_answer,
        str,
    ):
        raise RuntimeError(
            "Harbor agent returned "
            "an invalid answer."
        )

    # ========================================================
    # 9. Output guardrail
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

    elif (
        output_result.status
        in {
            "block",
            "escalate",
        }
    ):
        safe_answer = (
            SAFE_OUTPUT_FALLBACK
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
    # 10. Persist escalation ticket
    # ========================================================

    escalation_required = bool(
        result.get(
            "escalation_required",
            False,
        )
    )

    escalation_ticket = None

    if (
        action == "escalate"
        and escalation_required
    ):
        escalation_ticket = (
            create_escalation_ticket(
                user_id=user_id,

                conversation_id=(
                    active_conversation_id
                ),

                message=safe_message,

                severity=result.get(
                    "severity",
                    "medium",
                ),
            )
        )

    # ========================================================
    # 11. Persist safe assistant response
    # ========================================================

    finalize_conversation_turn(
        conversation_id=(
            active_conversation_id
        ),

        assistant_message=(
            safe_answer
        ),
    )

    # ========================================================
    # 12. Update summary memory
    # ========================================================

    try:
        update_summary_memory(
            active_conversation_id
        )

    except Exception:
        # We will replace this with structured logging during
        # Harbor production hardening.
        pass

    # ========================================================
    # 13. Return safe customer response
    # ========================================================

    return AgentResponse(
        answer=safe_answer,

        action=action,

        severity=result.get(
            "severity",
            "low",
        ),

        citations=result.get(
            "citations",
            [],
        ),

        escalation_required=(
            escalation_required
        ),

        conversation_id=(
            active_conversation_id
        ),

        ticket_id=(
            str(
                escalation_ticket["id"]
            )
            if escalation_ticket
            else None
        ),

        ticket_status=(
            escalation_ticket.get(
                "status"
            )
            if escalation_ticket
            else None
        ),

        approval_status=(
            escalation_ticket.get(
                "approval_status"
            )
            if escalation_ticket
            else None
        ),
    )