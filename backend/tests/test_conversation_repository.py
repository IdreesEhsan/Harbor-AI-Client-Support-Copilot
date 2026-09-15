import pytest

from app.repositories.conversations import (
    save_message,
)


def test_save_message_rejects_empty_content():
    with pytest.raises(ValueError):
        save_message(
            conversation_id="conversation-123",
            role="user",
            content="   ",
        )


def test_save_message_rejects_unknown_role():
    with pytest.raises(ValueError):
        save_message(
            conversation_id="conversation-123",
            role="developer",
            content="Hello",
        )