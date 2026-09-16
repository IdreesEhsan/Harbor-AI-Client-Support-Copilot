from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.dependencies.auth import get_current_user
from app.rag.service import answer_question
from app.schemas.rag import (
    RAGRequest,
    RAGResponse,
)


settings = get_settings()


router = APIRouter(
    prefix="/rag",
    tags=["RAG"],
)


@router.post(
    "/ask",
    response_model=RAGResponse,
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
    """
    Answer an authenticated question using Harbor's
    grounded RAG system.

    Production protections:
    - authentication;
    - request validation;
    - rate limiting;
    - defensive input-size limits;
    - safe exception responses.
    """

    try:
        question = (
            payload.question.strip()
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

        return answer_question(
            question=question,
        )

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=str(exc),
        ) from exc

    except Exception as exc:
        # Provider/database internals must never be returned
        # directly to API clients.
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Unable to process the "
                "knowledge-base question."
            ),
        ) from exc