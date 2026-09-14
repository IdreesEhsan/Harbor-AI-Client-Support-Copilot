from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from app.rag.service import answer_question
from app.schemas.rag import (
    RAGRequest,
    RAGResponse,
)

# Reuse the authentication dependency already created in Phase 3.
# Change this import only if your existing auth dependency is located
# in another module.
from app.dependencies.auth import get_current_user


router = APIRouter(
    prefix="/rag",
    tags=["RAG"],
)


@router.post(
    "/ask",
    response_model=RAGResponse,
)
def ask_knowledge_base(
    payload: RAGRequest,
    current_user: dict = Depends(
        get_current_user
    ),
) -> RAGResponse:
    """
    Answer an authenticated user's question with Harbor's RAG system.
    """

    try:
        return answer_question(
            question=payload.question,
        )

    except Exception as exc:
        # Provider/database internals should not be exposed to clients.
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to process the knowledge-base question."
            ),
        ) from exc  