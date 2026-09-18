from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
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

from app.rag.analytics import (
    create_rag_feedback,
)

from app.rag.service import (
    answer_question,
)

from app.schemas.rag import (
    RAGFeedbackRequest,
    RAGFeedbackResponse,
    RAGRequest,
    RAGResponse,
)


settings = (
    get_settings()
)


router = APIRouter(
    prefix="/rag",

    tags=[
        "RAG",
    ],
)


# ============================================================
# ASK
# ============================================================

@router.post(
    "/ask",

    response_model=(
        RAGResponse
    ),
)
@limiter.limit(
    settings.rag_rate_limit
)
def ask_knowledge_base(
    request: Request,

    payload: RAGRequest,

    current_user: dict = Depends(
        get_current_user
    ),
) -> RAGResponse:
    try:
        question = (
            payload
            .question
            .strip()
        )


        if not question:
            raise HTTPException(
                status_code=(
                    status.HTTP_400_BAD_REQUEST
                ),

                detail=(
                    "Question cannot be empty."
                ),
            )


        if (
            len(question)
            > settings.llm_max_input_characters
        ):
            raise HTTPException(
                status_code=(
                    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                ),

                detail=(
                    "Question exceeds the maximum "
                    "allowed input size."
                ),
            )


        requester_role = str(
            current_user.get(
                "role",
                "customer",
            )
        )


        return (
            answer_question(
                question=question,

                requester_role=(
                    requester_role
                ),
            )
        )


    except HTTPException:
        raise


    except ValueError as exc:
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
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),

            detail=(
                "Unable to process the "
                "knowledge-base question."
            ),
        ) from exc


# ============================================================
# FEEDBACK
# ============================================================

@router.post(
    "/feedback",

    response_model=(
        RAGFeedbackResponse
    ),

    status_code=(
        status.HTTP_201_CREATED
    ),
)
def submit_rag_feedback(
    payload: RAGFeedbackRequest,

    current_user: dict = Depends(
        get_current_user
    ),
):
    try:
        record = (
            create_rag_feedback(
                user_id=str(
                    current_user[
                        "id"
                    ]
                ),

                question=(
                    payload.question
                ),

                answer=(
                    payload.answer
                ),

                rating=(
                    payload.rating
                ),

                comment=(
                    payload.comment
                ),

                source_names=(
                    payload.source_names
                ),
            )
        )


        return (
            RAGFeedbackResponse(
                id=str(
                    record[
                        "id"
                    ]
                ),

                rating=str(
                    record[
                        "rating"
                    ]
                ),

                message=(
                    "Thank you. Your feedback "
                    "has been recorded."
                ),
            )
        )


    except ValueError as exc:
        raise HTTPException(
            status_code=400,

            detail=str(
                exc
            ),
        ) from exc