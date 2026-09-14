from unittest.mock import patch

from fastapi.testclient import TestClient

from app.dependencies.auth import get_current_user
from app.main import app


client = TestClient(app)


def fake_current_user():
    return {
        "id": "user-123",
        "email": "test@example.com",
    }


app.dependency_overrides[
    get_current_user
] = fake_current_user


@patch(
    "app.api.agent.run_agent"
)
def test_agent_chat_endpoint(
    mock_run_agent,
):
    from app.agent.schemas import AgentResponse

    mock_run_agent.return_value = (
        AgentResponse(
            answer="Refunds take 5 to 10 business days.",
            action="answer",
            severity="low",
            citations=[],
            escalation_required=False,
        )
    )

    response = client.post(
        "/api/v1/agent/chat",
        json={
            "message": (
                "How long does a refund take?"
            )
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["action"] == "answer"
    assert data["severity"] == "low"


def test_agent_chat_rejects_blank_message():
    response = client.post(
        "/api/v1/agent/chat",
        json={
            "message": ""
        },
    )

    assert response.status_code == 422