from app.agent.graph import harbor_graph
from app.agent.schemas import AgentResponse


def run_agent(
    message: str,
    user_id: str,
    conversation_id: str | None = None,
) -> AgentResponse:
    """
    Run Harbor's LangGraph workflow and convert internal graph state
    into the public response returned by the API.
    """

    message = message.strip()

    if not message:
        raise ValueError("Message cannot be empty.")

    initial_state = {
        "question": message,
        "user_id": user_id,
        "conversation_id": conversation_id,
    }

    result = harbor_graph.invoke(
        initial_state
    )

    action = result.get("action")

    if action not in {
        "answer",
        "clarify",
        "escalate",
    }:
        raise RuntimeError(
            "Harbor agent returned an invalid action."
        )

    answer = result.get("answer")

    if not answer:
        raise RuntimeError(
            "Harbor agent returned no answer."
        )

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
    )