from fastapi import APIRouter, Depends, HTTPException

from app.agent.schemas import (
    AgentRequest,
    AgentResponse,
)
from app.agent.service import run_agent
from app.dependencies.auth import get_current_user


router = APIRouter(
    prefix="/agent",
    tags=["Agent"],
)


@router.post(
    "/chat",
    response_model=AgentResponse,
)
def agent_chat(
    payload: AgentRequest,
    current_user: dict = Depends(
        get_current_user
    ),
) -> AgentResponse:
    """
    Run an authenticated user message through Harbor's LangGraph agent.
    """

    try:
        user_id = str(
            current_user["id"]
        )

        return run_agent(
            message=payload.message,
            user_id=user_id,
            conversation_id=(
                payload.conversation_id
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to process the "
                "agent request."
            ),
        ) from exc