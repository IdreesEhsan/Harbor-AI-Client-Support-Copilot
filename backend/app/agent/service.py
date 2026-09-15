from app.agent.graph import harbor_graph
from app.agent.schemas import AgentResponse
from app.core.config import get_settings
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


def run_agent(
    message: str,
    user_id: str,
    conversation_id: str | None = None,
) -> AgentResponse:
    """
    Run one persistent Harbor conversation turn.

    Harbor loads short-term buffer memory and long-term summary memory,
    executes the LangGraph agent, persists the completed turn, and then
    updates summary memory when the conversation is long enough.
    """

    settings = get_settings()

    message = message.strip()

    if not message:
        raise ValueError(
            "Message cannot be empty."
        )

    # Create a new conversation or verify that the supplied conversation
    # belongs to the authenticated user.
    conversation = prepare_conversation(
        user_id=user_id,
        conversation_id=conversation_id,
    )

    active_conversation_id = str(
        conversation["id"]
    )

    # Load previous conversation turns BEFORE storing the current message.
    # This prevents the current question from appearing both in history
    # and as the current LangGraph question.
    recent_messages = load_recent_history(
        conversation_id=active_conversation_id,
        limit=settings.memory_buffer_size,
    )

    history = format_history(
        recent_messages
    )

    # Load compressed long-term memory from older conversation turns.
    # New conversations will simply have no existing summary.
    conversation_summary = (
        load_conversation_summary(
            active_conversation_id
        )
    )

    # Persist the current user message only after previous history has
    # been loaded so it does not enter the buffer twice.
    save_user_message(
        conversation_id=active_conversation_id,
        message=message,
    )

    # Both memory layers are now available to LangGraph:
    # - history: recent short-term buffer
    # - conversation_summary: compressed older context
    initial_state = {
        "question": message,
        "user_id": user_id,
        "conversation_id": active_conversation_id,
        "history": history,
        "conversation_summary": (
            conversation_summary or ""
        ),
    }

    result = harbor_graph.invoke(
        initial_state
    )

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

    answer = result.get(
        "answer"
    )

    if not answer:
        raise RuntimeError(
            "Harbor agent returned no answer."
        )

    # Store Harbor's response only after LangGraph completes
    # successfully.
    finalize_conversation_turn(
        conversation_id=active_conversation_id,
        assistant_message=answer,
    )

    # After the complete user/assistant turn has been persisted,
    # compress older messages into long-term summary memory when needed.
    #
    # Summary-memory failure must not turn an otherwise successful
    # customer-support response into an API failure. Structured logging
    # will replace this silent fallback during production hardening.
    try:
        update_summary_memory(
            active_conversation_id
        )
    except Exception:
        pass

    return AgentResponse(
        answer=answer,
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
        conversation_id=active_conversation_id,
    )