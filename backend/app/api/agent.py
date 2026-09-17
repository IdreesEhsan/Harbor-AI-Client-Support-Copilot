import json
import queue
import threading

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)

from fastapi.responses import (
    StreamingResponse,
)

from app.agent.schemas import (
    AgentRequest,
    AgentResponse,
)

from app.agent.service import (
    run_agent,
)

from app.agent.streaming import (
    clear_stream_emitter,
    set_stream_emitter,
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


# ============================================================
# COMMON INPUT VALIDATION
# ============================================================

def validate_agent_input(
    payload: AgentRequest,
) -> None:
    """
    Apply Harbor's explicit API-level LLM input boundary.
    """

    if (
        len(payload.message)
        > settings.llm_max_input_characters
    ):
        raise HTTPException(
            status_code=(
                status
                .HTTP_413_REQUEST_ENTITY_TOO_LARGE
            ),

            detail=(
                "Message exceeds the maximum "
                "allowed input size."
            ),
        )


# ============================================================
# EXISTING NON-STREAMING ENDPOINT
# ============================================================

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
    Run one authenticated Harbor conversation turn using
    Harbor's original non-streaming response mode.

    This endpoint remains available for compatibility.
    """

    try:
        validate_agent_input(
            payload
        )


        user_id = str(
            current_user["id"]
        )


        return run_agent(
            message=(
                payload.message
            ),

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

            detail=(
                "Conversation not found."
            ),
        ) from exc


    except HTTPException:
        raise


    except (
        ValueError,
        TypeError,
    ) as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=str(
                exc
            ),
        ) from exc


    except Exception as exc:
        raise HTTPException(
            status_code=(
                status
                .HTTP_500_INTERNAL_SERVER_ERROR
            ),

            detail=(
                "Unable to process the "
                "agent request."
            ),
        ) from exc


# ============================================================
# STREAM HELPERS
# ============================================================

def format_sse_event(
    event_name: str,
    data: dict,
) -> str:
    """
    Serialize one Server-Sent Events frame.
    """

    serialized = json.dumps(
        data,
        ensure_ascii=False,
    )

    return (
        f"event: {event_name}\n"
        f"data: {serialized}\n\n"
    )


# ============================================================
# STREAMING ENDPOINT
# ============================================================

@router.post(
    "/chat/stream",
)
@limiter.limit(
    settings.agent_rate_limit
)
def agent_chat_stream(
    request: Request,
    payload: AgentRequest,
    current_user: dict = Depends(
        get_current_user
    ),
):
    """
    Run Harbor's existing agent workflow while streaming
    model-generated answer chunks to the frontend.

    Harbor still uses the same run_agent() implementation for:

    - conversation memory;
    - LangGraph routing;
    - RAG;
    - input guardrails;
    - output guardrails;
    - ticket-confirmation workflow;
    - citations;
    - ticket creation.

    Only the transport of generated text changes.
    """

    validate_agent_input(
        payload
    )


    user_id = str(
        current_user["id"]
    )


    event_queue: queue.Queue = (
        queue.Queue()
    )


    FINISHED = object()


    # ========================================================
    # WORKER
    # ========================================================

    def worker() -> None:

        def emit_token(
            token: str,
        ) -> None:

            event_queue.put(
                (
                    "token",
                    {
                        "content":
                            token,
                    },
                )
            )


        try:
            set_stream_emitter(
                emit_token
            )


            result = run_agent(
                message=(
                    payload.message
                ),

                user_id=(
                    user_id
                ),

                conversation_id=(
                    payload
                    .conversation_id
                ),
            )


            event_queue.put(
                (
                    "final",
                    result.model_dump(
                        mode="json"
                    ),
                )
            )


        except ConversationNotFoundError:

            event_queue.put(
                (
                    "error",
                    {
                        "detail":
                            "Conversation not found.",
                    },
                )
            )


        except (
            ValueError,
            TypeError,
        ) as exc:

            event_queue.put(
                (
                    "error",
                    {
                        "detail":
                            str(exc),
                    },
                )
            )


        except Exception:

            event_queue.put(
                (
                    "error",
                    {
                        "detail": (
                            "Unable to process "
                            "the agent request."
                        ),
                    },
                )
            )


        finally:
            clear_stream_emitter()

            event_queue.put(
                FINISHED
            )


    # ========================================================
    # SSE GENERATOR
    # ========================================================

    def event_generator():

        thread = threading.Thread(
            target=worker,
            daemon=True,
        )

        thread.start()


        yield format_sse_event(
            "start",
            {
                "streaming":
                    True,
            },
        )


        while True:

            item = (
                event_queue.get()
            )


            if item is FINISHED:
                break


            event_name, data = item


            yield format_sse_event(
                event_name,
                data,
            )


        yield format_sse_event(
            "done",
            {
                "streaming":
                    False,
            },
        )


    return StreamingResponse(
        event_generator(),

        media_type=(
            "text/event-stream"
        ),

        headers={
            "Cache-Control":
                "no-cache",

            "Connection":
                "keep-alive",

            # Prevent nginx-style reverse proxies from
            # buffering Harbor's streamed chunks.
            "X-Accel-Buffering":
                "no",
        },
    )