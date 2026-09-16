from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)

from app.agent.schemas import (
    AgentRequest,
    AgentResponse,
)
from app.agent.service import (
    run_agent,
)
from app.core.config import (
    get_settings,
)
from app.core.rate_limit import (
    limiter,
)
from app.dependencies.auth import (
    get_current_user,
)
from app.services.conversation_service import (
    ConversationNotFoundError,
)


settings = get_settings()


router = APIRouter(
    prefix="/agent",
    tags=["Agent"],
)


@router.post(
    "/chat",
    response_model=AgentResponse,
)
@limiter.limit(
    settings.agent_rate_limit
)
def agent_chat(
    request: Request,
    payload: AgentRequest,
    current_user: dict = Depends(
        get_current_user
    ),
) -> AgentResponse:
    """
    Run one authenticated Harbor conversation turn.

    Production protections:
    - JWT authentication
    - per-client rate limiting
    - request schema validation
    - conversation ownership validation
    - input/output guardrails inside the service layer
    - graph-step and tool-call execution limits
    - controlled exception handling

    The request object is required by SlowAPI so the rate
    limiter can identify and enforce the configured limit.
    """

    try:
        user_id = str(
            current_user["id"]
        )

        # ----------------------------------------------------
        # Defensive input-size check
        # ----------------------------------------------------
        #
        # Pydantic already limits AgentRequest.message, but
        # keeping this explicit production boundary makes
        # Harbor's LLM usage policy clear.
        if (
            len(payload.message)
            > settings.llm_max_input_characters
        ):
            raise HTTPException(
                status_code=(
                    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                ),
                detail=(
                    "Message exceeds the maximum allowed "
                    "input size."
                ),
            )

        return run_agent(
            message=payload.message,
            user_id=user_id,
            conversation_id=(
                payload.conversation_id
            ),
        )

    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail="Conversation not found.",
        ) from exc

    except HTTPException:
        # Preserve deliberate FastAPI responses such as
        # 413 rather than converting them into generic 500s.
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=str(exc),
        ) from exc

    except TypeError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Unable to process the agent request."
            ),
        ) from exc