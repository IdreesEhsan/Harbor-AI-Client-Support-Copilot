from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from app.dependencies.auth import (
    require_roles,
)

from app.services.conversation_service import (
    ConversationNotFoundError,
    get_user_conversation_history,
    list_user_conversations,
)


router = APIRouter(
    prefix="/conversations",
)


# ============================================================
# MY AI CONVERSATIONS
# ============================================================

@router.get("")
def get_my_conversations(
    current_user=Depends(
        require_roles(
            "customer",
        )
    ),
):
    """
    Return the authenticated customer's AI sidebar history.
    """

    return list_user_conversations(
        user_id=str(
            current_user["id"]
        ),
        limit=50,
    )


# ============================================================
# ONE AI CONVERSATION
# ============================================================

@router.get(
    "/{conversation_id}"
)
def get_my_conversation(
    conversation_id: UUID,
    current_user=Depends(
        require_roles(
            "customer",
        )
    ),
):
    """
    Load one owned AI conversation including assistant
    metadata such as sources/citations.
    """

    try:
        return (
            get_user_conversation_history(
                user_id=str(
                    current_user["id"]
                ),

                conversation_id=str(
                    conversation_id
                ),
            )
        )

    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=str(exc),
        ) from exc