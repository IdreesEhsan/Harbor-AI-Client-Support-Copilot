from app.agent.state import HarborAgentState


def test_agent_state_can_hold_request_data():
    state: HarborAgentState = {
        "user_id": "user-123",
        "conversation_id": None,
        "question": "How long does a refund take?",
    }

    assert state["user_id"] == "user-123"

    assert (
        state["question"]
        == "How long does a refund take?"
    )


def test_agent_state_can_hold_router_output():
    state: HarborAgentState = {
        "question": "I need a human agent.",
        "action": "escalate",
        "reason": "User explicitly requested human support.",
        "severity": "medium",
        "confidence": 0.98,
        "escalation_required": True,
    }

    assert state["action"] == "escalate"

    assert (
        state["escalation_required"]
        is True
    )