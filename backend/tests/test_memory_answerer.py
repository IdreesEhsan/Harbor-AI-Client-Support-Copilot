from unittest.mock import MagicMock, patch

import pytest

from app.agent.memory_answerer import (
    MEMORY_NO_ANSWER,
    MemoryAnswerError,
    answer_from_memory,
)


@patch(
    "app.agent.memory_answerer.get_groq_client"
)
def test_memory_answer_uses_summary(
    mock_get_client,
):
    """
    Harbor should be able to recall information contained
    in long-term conversation summary memory.
    """

    client = MagicMock()
    response = MagicMock()

    response.choices[0].message.content = (
        "Your order reference was ORD-7842."
    )

    client.chat.completions.create.return_value = (
        response
    )

    mock_get_client.return_value = client

    answer = answer_from_memory(
        question=(
            "What was my order reference?"
        ),
        history=[],
        conversation_summary=(
            "The user previously provided order "
            "reference ORD-7842."
        ),
    )

    assert answer == (
        "Your order reference was ORD-7842."
    )

    call_kwargs = (
        client
        .chat
        .completions
        .create
        .call_args
        .kwargs
    )

    prompt = (
        call_kwargs["messages"][1]["content"]
    )

    assert "ORD-7842" in prompt
    assert (
        "What was my order reference?"
        in prompt
    )


@patch(
    "app.agent.memory_answerer.get_groq_client"
)
def test_memory_answer_uses_recent_buffer(
    mock_get_client,
):
    """
    Harbor should also recall information from the
    recent short-term conversation buffer.
    """

    client = MagicMock()
    response = MagicMock()

    response.choices[0].message.content = (
        "You said the product was damaged."
    )

    client.chat.completions.create.return_value = (
        response
    )

    mock_get_client.return_value = client

    answer = answer_from_memory(
        question=(
            "What reason did I give for the refund?"
        ),
        history=[
            {
                "role": "user",
                "content": (
                    "The refund is for a damaged product."
                ),
            }
        ],
        conversation_summary=None,
    )

    assert answer == (
        "You said the product was damaged."
    )


@patch(
    "app.agent.memory_answerer.get_groq_client"
)
def test_memory_answer_combines_summary_and_buffer(
    mock_get_client,
):
    """
    Both memory layers should be available to the
    memory-answer model.
    """

    client = MagicMock()
    response = MagicMock()

    response.choices[0].message.content = (
        "Your order reference was ORD-7842."
    )

    client.chat.completions.create.return_value = (
        response
    )

    mock_get_client.return_value = client

    answer_from_memory(
        question=(
            "Remind me what my order reference was."
        ),
        history=[
            {
                "role": "user",
                "content": (
                    "Support asked me to wait two days."
                ),
            }
        ],
        conversation_summary=(
            "The user's order reference is ORD-7842."
        ),
    )

    call_kwargs = (
        client
        .chat
        .completions
        .create
        .call_args
        .kwargs
    )

    prompt = (
        call_kwargs["messages"][1]["content"]
    )

    assert "ORD-7842" in prompt
    assert (
        "Support asked me to wait two days."
        in prompt
    )


@patch(
    "app.agent.memory_answerer.get_groq_client"
)
def test_no_memory_returns_fallback_without_groq(
    mock_get_client,
):
    """
    Harbor should not spend an LLM call when no conversation
    memory exists.
    """

    answer = answer_from_memory(
        question=(
            "What was my order reference?"
        ),
        history=[],
        conversation_summary=None,
    )

    assert answer == MEMORY_NO_ANSWER

    mock_get_client.assert_not_called()


@patch(
    "app.agent.memory_answerer.get_groq_client"
)
def test_empty_groq_memory_answer_raises_error(
    mock_get_client,
):
    """
    An empty Groq response should not silently become a
    successful memory answer.
    """

    client = MagicMock()
    response = MagicMock()

    response.choices[0].message.content = ""

    client.chat.completions.create.return_value = (
        response
    )

    mock_get_client.return_value = client

    with pytest.raises(
        MemoryAnswerError
    ):
        answer_from_memory(
            question="What was my order reference?",
            conversation_summary=(
                "Order reference ORD-7842."
            ),
        )


def test_memory_answer_rejects_empty_question():
    """
    Blank questions should fail before calling Groq.
    """

    with pytest.raises(
        ValueError,
        match="Question cannot be empty",
    ):
        answer_from_memory(
            question="   ",
        )