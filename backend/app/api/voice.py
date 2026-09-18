import logging
from typing import Any

from fastapi import (
    APIRouter,
    HTTPException,
    status,
)
from pydantic import (
    BaseModel,
    Field,
)

from app.rag.service import (
    answer_question,
)


logger = logging.getLogger(
    "harbor.voice"
)


router = APIRouter(
    prefix="/voice",
    tags=["Voice"],
)


# ============================================================
# REQUEST / RESPONSE SCHEMAS
# ============================================================

class VoiceKnowledgeRequest(
    BaseModel
):
    """
    Request sent by the Retell voice agent when the caller
    asks Harbor an informational support question.
    """

    query: str = Field(
        min_length=1,
        max_length=1000,
    )


class VoiceKnowledgeResponse(
    BaseModel
):
    """
    Voice-friendly representation of Harbor's RAG answer.
    """

    success: bool

    answer: str

    grounded: bool

    sources: list[str] = Field(
        default_factory=list
    )


# ============================================================
# HELPERS
# ============================================================

def _clean_query(
    query: str,
) -> str:
    """
    Normalize a caller query before sending it into Harbor's
    RAG pipeline.
    """

    if not isinstance(
        query,
        str,
    ):
        raise TypeError(
            "Voice support query must be a string."
        )

    query = query.strip()

    if not query:
        raise ValueError(
            "Voice support query cannot be empty."
        )

    return query


def _extract_sources(
    citations: list[Any],
) -> list[str]:
    """
    Convert Harbor citation objects into a simple unique
    list of source names suitable for a Retell response.

    Retell does not need the complete citation metadata
    because citations are not normally spoken aloud.
    """

    sources: list[str] = []

    for citation in citations:
        source = getattr(
            citation,
            "source",
            None,
        )

        if source is None:
            continue

        source_text = str(
            source
        ).strip()

        if (
            source_text
            and source_text
            not in sources
        ):
            sources.append(
                source_text
            )

    return sources


# ============================================================
# SEARCH HARBOR KNOWLEDGE
# ============================================================

@router.post(
    "/search-knowledge",
    response_model=(
        VoiceKnowledgeResponse
    ),
    status_code=(
        status.HTTP_200_OK
    ),
)
def search_support_knowledge(
    payload: VoiceKnowledgeRequest,
) -> VoiceKnowledgeResponse:
    """
    Search Harbor's existing support knowledge base.

    Architecture:

        Retell
           ↓
        Harbor voice API
           ↓
        Existing Harbor RAG
           ↓
        MiniLM / pgvector
           ↓
        Groq grounded answer
           ↓
        Voice-friendly result

    The web interface and voice interface therefore use the
    same company knowledge source.
    """

    try:
        query = (
            _clean_query(
                payload.query
            )
        )

        result = (
            answer_question(
                question=query
            )
        )

        sources = (
            _extract_sources(
                result.citations
                or []
            )
        )

        logger.info(
            (
                "Voice knowledge search completed | "
                "grounded=%s | "
                "retrieved_chunks=%s | "
                "source_count=%s"
            ),
            result.grounded,
            result.retrieved_chunks,
            len(
                sources
            ),
        )

        return VoiceKnowledgeResponse(
            success=True,
            answer=result.answer,
            grounded=result.grounded,
            sources=sources,
        )

    except (
        TypeError,
        ValueError,
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
        logger.exception(
            "Voice knowledge search failed."
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Harbor could not search the "
                "support knowledge base."
            ),
        ) from exc


# ============================================================
# HEALTH / INTEGRATION TEST
# ============================================================

@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
)
def voice_health() -> dict[str, str]:
    """
    Small endpoint for verifying that Harbor's voice API
    router is registered correctly.
    """

    return {
        "status": "ok",
        "service": "harbor-voice",
    }