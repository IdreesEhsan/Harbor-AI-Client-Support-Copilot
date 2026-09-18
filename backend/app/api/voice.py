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
    StrictBool,
)

from app.rag.service import (
    answer_question,
)

from app.services.voice_service import (
    VoiceCustomerNotFoundError,
    VoiceTicketConfirmationRequiredError,
    VoiceTicketCreationError,
    create_voice_support_ticket,
)


logger = logging.getLogger(
    "harbor.voice"
)


router = APIRouter(
    prefix="/voice",
    tags=[
        "Voice",
    ],
)


# ============================================================
# RAG REQUEST / RESPONSE
# ============================================================

class VoiceKnowledgeRequest(
    BaseModel
):
    query: str = Field(
        min_length=1,
        max_length=1000,
    )


class VoiceKnowledgeResponse(
    BaseModel
):
    success: bool

    answer: str

    grounded: bool

    sources: list[str] = Field(
        default_factory=list
    )


# ============================================================
# TICKET REQUEST / RESPONSE
# ============================================================

class VoiceTicketRequest(
    BaseModel
):
    """
    Ticket request created only after the caller explicitly
    confirms that Harbor should create a support ticket.
    """

    customer_email: str = Field(
        min_length=3,
        max_length=320,
    )

    issue: str = Field(
        min_length=1,
        max_length=5000,
    )

    call_id: str = Field(
        min_length=1,
        max_length=255,
    )

    confirmed: StrictBool

    severity: str = Field(
        default="medium",
        min_length=1,
        max_length=20,
    )


class VoiceTicketResponse(
    BaseModel
):
    success: bool

    ticket_id: str

    status: str

    approval_status: str

    severity: str

    message: str


# ============================================================
# HELPERS
# ============================================================

def _clean_query(
    query: str,
) -> str:
    if not isinstance(
        query,
        str,
    ):
        raise TypeError(
            (
                "Voice support query "
                "must be a string."
            )
        )

    query = (
        query.strip()
    )

    if not query:
        raise ValueError(
            (
                "Voice support query "
                "cannot be empty."
            )
        )

    return query


def _extract_sources(
    citations: list[Any],
) -> list[str]:
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
# HEALTH
# ============================================================

@router.get(
    "/health",
    status_code=(
        status.HTTP_200_OK
    ),
)
def voice_health() -> dict[
    str,
    str,
]:
    return {
        "status":
            "ok",

        "service":
            "harbor-voice",
    }


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
    Search Harbor's existing RAG knowledge base for a Retell
    voice caller.
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

        return (
            VoiceKnowledgeResponse(
                success=True,

                answer=(
                    result.answer
                ),

                grounded=(
                    result.grounded
                ),

                sources=sources,
            )
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
            (
                "Voice knowledge "
                "search failed."
            )
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),

            detail=(
                "Harbor could not search "
                "the support knowledge base."
            ),
        ) from exc


# ============================================================
# CREATE SUPPORT TICKET
# ============================================================

@router.post(
    "/create-ticket",
    response_model=(
        VoiceTicketResponse
    ),
    status_code=(
        status.HTTP_201_CREATED
    ),
)
def create_support_ticket(
    payload: VoiceTicketRequest,
) -> VoiceTicketResponse:
    """
    Create a customer-confirmed support ticket from Retell.

    Important:

    This endpoint creates only Harbor's internal
    pending-approval ticket.

    It cannot approve or execute the customer's requested
    action.
    """

    try:
        ticket = (
            create_voice_support_ticket(
                customer_email=(
                    payload
                    .customer_email
                ),

                issue=(
                    payload.issue
                ),

                call_id=(
                    payload.call_id
                ),

                confirmed=(
                    payload.confirmed
                ),

                severity=(
                    payload.severity
                ),
            )
        )


        return (
            VoiceTicketResponse(
                success=True,

                ticket_id=str(
                    ticket[
                        "id"
                    ]
                ),

                status=str(
                    ticket.get(
                        "status",
                        "pending_approval",
                    )
                ),

                approval_status=str(
                    ticket.get(
                        "approval_status",
                        "pending",
                    )
                ),

                severity=str(
                    ticket.get(
                        "severity",
                        "medium",
                    )
                ),

                message=(
                    "Your support ticket has "
                    "been created and sent to "
                    "a Harbor support agent "
                    "for review."
                ),
            )
        )


    except (
        VoiceCustomerNotFoundError,
    ) as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),

            detail=str(
                exc
            ),
        ) from exc


    except (
        VoiceTicketConfirmationRequiredError,
    ) as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),

            detail=str(
                exc
            ),
        ) from exc


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


    except VoiceTicketCreationError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),

            detail=str(
                exc
            ),
        ) from exc


    except Exception as exc:
        logger.exception(
            (
                "Unexpected voice ticket "
                "creation failure."
            )
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),

            detail=(
                "Harbor could not create "
                "the support ticket."
            ),
        ) from exc