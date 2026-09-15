from unittest.mock import patch

import pytest

from app.services.conversation_service import (
    ConversationNotFoundError,
    prepare_conversation,
)


@patch(
    "app.services.conversation_service.create_conversation"
)
def test_prepare_creates_new_conversation(
    mock_create,
):
    mock_create.return_value = {
        "id": "conversation-new",
        "user_id": "user-123",
    }

    result = prepare_conversation(
        user_id="user-123",
    )

    assert result["id"] == "conversation-new"

    mock_create.assert_called_once_with(
        user_id="user-123",
    )


@patch(
    "app.services.conversation_service.get_conversation"
)
def test_prepare_existing_conversation(
    mock_get,
):
    mock_get.return_value = {
        "id": "conversation-123",
        "user_id": "user-123",
    }

    result = prepare_conversation(
        user_id="user-123",
        conversation_id="conversation-123",
    )

    assert result["id"] == "conversation-123"


@patch(
    "app.services.conversation_service.get_conversation"
)
def test_prepare_rejects_unavailable_conversation(
    mock_get,
):
    mock_get.return_value = None

    with pytest.raises(
        ConversationNotFoundError
    ):
        prepare_conversation(
            user_id="user-123",
            conversation_id="not-owned",
        )