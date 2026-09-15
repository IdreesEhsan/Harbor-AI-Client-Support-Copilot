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


# Safe deterministic response used when Harbor refuses to
# expose generated output.
SAFE_OUTPUT_FALLBACK = (
    "I couldn't return that response safely. "
    "Please rephrase your support question or "
    "ask to speak with a human support agent."
)


# Safe deterministic response used when Harbor stops an
# agent workflow because its graph-step execution budget
# has been exhausted.
#
# Do not expose internal limits, implementation details,
# stack traces, or exception text to the client.
SAFE_EXECUTION_LIMIT_FALLBACK = (
    "I couldn't complete this request safely within the "
    "allowed processing limits. Please try again or ask "
    "to speak with a human support agent."
)


def run_agent(
    message: str,
    user_id: str,
    conversation_id: str | None = None,
) -> AgentResponse:
    """
    Run one persistent Harbor conversation turn.

    Security flow:

    1. Validate the raw request.
    2. Apply service-level input guardrails.
    3. Create or validate the conversation.
    4. Load short-term and long-term memory.
    5. Persist only safe/sanitized user content.
    6. Execute LangGraph with protected input and execution
       failure handling.
    7. Validate the graph contract.
    8. Apply output guardrails.
    9. Persist only the safe final assistant response.
    10. Update summary memory.
    11. Return only the safe response to the client.

    LangGraph also maintains its own input guardrail as
    defense in depth.
    """

    settings = get_settings()

    # --------------------------------------------------------
    # 1. Basic request validation
    # --------------------------------------------------------

    if not isinstance(message, str):
        raise TypeError(
            "Message must be a string."
        )

    message = message.strip()

    if not message:
        raise ValueError(
            "Message cannot be empty."
        )

    # --------------------------------------------------------
    # 2. Service-level input guardrail
    # --------------------------------------------------------
    #
    # This is Harbor's first trust boundary.
    #
    # Raw PII and credentials should not travel deeper into
    # the application when a sanitized representation can be
    # used instead.
    guardrail_result = run_input_guardrails(
        message
    )

    if guardrail_result.status == "redact":
        safe_message = (
            guardrail_result.redacted_content
            or message
        )
    else:
        safe_message = message

    # --------------------------------------------------------
    # 3. Prepare conversation
    # --------------------------------------------------------

    conversation = prepare_conversation(
        user_id=user_id,
        conversation_id=conversation_id,
    )

    active_conversation_id = str(
        conversation["id"]
    )

    # --------------------------------------------------------
    # 4. Load existing memory
    # --------------------------------------------------------
    #
    # Previous history is loaded BEFORE storing the current
    # message so the current question does not appear twice.
    recent_messages = load_recent_history(
        conversation_id=active_conversation_id,
        limit=settings.memory_buffer_size,
    )

    history = format_history(
        recent_messages
    )

    conversation_summary = (
        load_conversation_summary(
            active_conversation_id
        )
    )

    # --------------------------------------------------------
    # 5. Safe user-message persistence
    # --------------------------------------------------------
    #
    # save_user_message() has its own guardrail check as a
    # second persistence-specific security boundary.
    #
    # Safe:
    #     stored normally
    #
    # Redacted:
    #     only sanitized content is stored
    #
    # Blocked:
    #     save_user_message() refuses the database write
    save_user_message(
        conversation_id=active_conversation_id,
        message=safe_message,
    )

    # --------------------------------------------------------
    # 6. Build LangGraph state
    # --------------------------------------------------------
    #
    # Redactable PII/credentials use safe_message.
    #
    # Blocked prompt-injection input is allowed to reach only
    # LangGraph's deterministic input guardrail so that the
    # graph can produce its controlled blocked response.
    #
    # Step 9.5 tests prove blocked content does not continue
    # into the Groq decision router.
    if guardrail_result.status == "block":
        graph_question = message
    else:
        graph_question = safe_message

    initial_state = {
        "question": graph_question,
        "user_id": user_id,
        "conversation_id": (
            active_conversation_id
        ),
        "history": history,
        "conversation_summary": (
            conversation_summary or ""
        ),

        # Explicitly initialize request-scoped execution
        # counters at the service boundary.
        #
        # This makes each run_agent() call start with a fresh
        # execution budget.
        "step_count": 0,
        "tool_call_count": 0,
        "execution_limit_reached": False,
    }

    # --------------------------------------------------------
    # 6A. Execute protected LangGraph workflow
    # --------------------------------------------------------
    #
    # controlled_node() raises ExecutionLimitExceededError
    # before a graph node is allowed to exceed Harbor's
    # configured step budget.
    #
    # Catch only this known safety exception here. We do not
    # broadly catch Exception because unrelated programming,
    # infrastructure, or database failures should not be
    # disguised as execution-limit events.
    try:
        result = harbor_graph.invoke(
            initial_state
        )

    except ExecutionLimitExceededError:
        # Convert the internal safety exception into the same
        # result contract consumed by the rest of this
        # service.
        #
        # This keeps execution-limit responses inside the
        # normal output-guardrail and safe-persistence path.
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

    # --------------------------------------------------------
    # 7. Validate LangGraph result contract
    # --------------------------------------------------------

    action = result.get(
        "action"
    )

    if action not in {
        "answer",
        "clarify",
        "escalate",
    }:
        raise RuntimeError(
            "Harbor agent returned an invalid action."
        )

    raw_answer = result.get(
        "answer"
    )

    if not raw_answer:
        raise RuntimeError(
            "Harbor agent returned no answer."
        )

    if not isinstance(raw_answer, str):
        raise RuntimeError(
            "Harbor agent returned an invalid answer."
        )

    # --------------------------------------------------------
    # 8. Output guardrail
    # --------------------------------------------------------
    #
    # This is the final security boundary between generated
    # agent output and both:
    #
    # - persistent conversation history
    # - the external API/client
    #
    # Execution-limit fallback responses intentionally pass
    # through this same boundary rather than bypassing normal
    # output security.
    #
    # Never persist or return raw_answer before this check.
    output_result = evaluate_output(
        raw_answer
    )

    if output_result.status == "allow":
        safe_answer = raw_answer

    elif output_result.status == "redact":
        safe_answer = (
            output_result.redacted_content
            or SAFE_OUTPUT_FALLBACK
        )

    elif output_result.status == "block":
        safe_answer = (
            SAFE_OUTPUT_FALLBACK
        )

    elif output_result.status == "escalate":
        # Output escalation is not currently generated by the
        # deterministic output guardrail, but we handle the
        # contract explicitly for future policy expansion.
        safe_answer = (
            SAFE_OUTPUT_FALLBACK
        )

    else:
        # Fail closed if the guardrail contract changes or an
        # unexpected state somehow reaches this boundary.
        safe_answer = (
            SAFE_OUTPUT_FALLBACK
        )

    # Defensive final validation.
    if not safe_answer.strip():
        safe_answer = (
            SAFE_OUTPUT_FALLBACK
        )

    # --------------------------------------------------------
    # 9. Persist only the SAFE assistant response
    # --------------------------------------------------------
    #
    # raw_answer must never be passed to this function.
    finalize_conversation_turn(
        conversation_id=active_conversation_id,
        assistant_message=safe_answer,
    )

    # --------------------------------------------------------
    # 10. Update long-term summary memory
    # --------------------------------------------------------
    #
    # Summary memory reads persisted conversation history.
    # Because both user and assistant persistence boundaries
    # now sanitize content, summary memory should consume only
    # safe persisted conversation data.
    #
    # Summary-memory failure remains non-critical.
    try:
        update_summary_memory(
            active_conversation_id
        )
    except Exception:
        # Production hardening will replace this silent
        # fallback with structured logging.
        pass

    # --------------------------------------------------------
    # 11. Return only safe output
    # --------------------------------------------------------

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
        escalation_required=result.get(
            "escalation_required",
            False,
        ),
        conversation_id=(
            active_conversation_id
        ),
    )