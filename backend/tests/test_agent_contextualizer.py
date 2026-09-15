from unittest.mock import MagicMock, patch

import pytest

from app.agent.contextualizer import (
    contextualize_question,
)


def test_contextualizer_returns_original_without_memory():
    """
    A standalone question with no conversational memory should
    be returned unchanged without making a Groq request.
    """

    question = (
        "How long does a refund take?"
    )

    result = contextualize_question(
        question=question,
        history=[],
        conversation_summary=None,
    )

    assert result == question


@patch(
    "app.agent.contextualizer.get_groq_client"
)
def test_contextualizer_uses_buffer_memory(
    mock_get_client,
):
    """
    Recent buffer memory should help Harbor rewrite an
    ambiguous follow-up into a standalone retrieval query.
    """

    client = MagicMock()

    response = MagicMock()

    response.choices[0].message.content = (
        "What should I do if a refund takes "
        "longer than the expected processing time?"
    )

    client.chat.completions.create.return_value = (
        response
    )

    mock_get_client.return_value = client

    history = [
        {
            "role": "user",
            "content": (
                "How long does a refund take?"
            ),
        },
        {
            "role": "assistant",
            "content": (
                "Refunds normally take 5 to 10 "
                "business days."
            ),
        },
    ]

    result = contextualize_question(
        question=(
            "What if it takes longer than that?"
        ),
        history=history,
        conversation_summary=None,
    )

    assert "refund" in result.lower()

    assert (
        "processing"
        in result.lower()
    )

    call_kwargs = (
        client
        .chat
        .completions
        .create
        .call_args
        .kwargs
    )

    user_prompt = (
        call_kwargs["messages"][1]["content"]
    )

    assert (
        "RECENT CONVERSATION"
        in user_prompt
    )

    assert (
        "How long does a refund take?"
        in user_prompt
    )

    assert (
        "What if it takes longer than that?"
        in user_prompt
    )


@patch(
    "app.agent.contextualizer.get_groq_client"
)
def test_contextualizer_uses_summary_memory(
    mock_get_client,
):
    """
    Long-term summary memory should still contextualize a
    question even when recent buffer history is empty.
    """

    client = MagicMock()

    response = MagicMock()

    response.choices[0].message.content = (
        "What should the user do about delayed "
        "refund REF-123?"
    )

    client.chat.completions.create.return_value = (
        response
    )

    mock_get_client.return_value = client

    summary = (
        "The user is waiting for refund REF-123. "
        "The refund was approved but has not arrived."
    )

    result = contextualize_question(
        question="What should I do now?",
        history=[],
        conversation_summary=summary,
    )

    assert (
        "REF-123"
        in result
    )

    call_kwargs = (
        client
        .chat
        .completions
        .create
        .call_args
        .kwargs
    )

    user_prompt = (
        call_kwargs["messages"][1]["content"]
    )

    assert (
        "CONVERSATION SUMMARY"
        in user_prompt
    )

    assert (
        summary
        in user_prompt
    )

    # Even with no recent buffer, the presence of summary
    # memory means Groq must be called.
    client.chat.completions.create.assert_called_once()


@patch(
    "app.agent.contextualizer.get_groq_client"
)
def test_contextualizer_uses_summary_and_buffer(
    mock_get_client,
):
    """
    Harbor should supply both long-term and short-term
    conversational memory when both are available.
    """

    client = MagicMock()

    response = MagicMock()

    response.choices[0].message.content = (
        "What should the user do after their bank "
        "reported no pending transaction for refund REF-123?"
    )

    client.chat.completions.create.return_value = (
        response
    )

    mock_get_client.return_value = client

    summary = (
        "The user is waiting for refund REF-123."
    )

    history = [
        {
            "role": "user",
            "content": (
                "I contacted my bank."
            ),
        },
        {
            "role": "assistant",
            "content": (
                "Does the bank show a pending transaction?"
            ),
        },
        {
            "role": "user",
            "content": "No.",
        },
    ]

    result = contextualize_question(
        question="What should I do now?",
        history=history,
        conversation_summary=summary,
    )

    assert (
        "REF-123"
        in result
    )

    call_kwargs = (
        client
        .chat
        .completions
        .create
        .call_args
        .kwargs
    )

    user_prompt = (
        call_kwargs["messages"][1]["content"]
    )

    assert (
        summary
        in user_prompt
    )

    assert (
        "I contacted my bank."
        in user_prompt
    )

    assert (
        "Does the bank show a pending transaction?"
        in user_prompt
    )

    assert (
        "What should I do now?"
        in user_prompt
    )


@patch(
    "app.agent.contextualizer.get_groq_client"
)
def test_contextualizer_falls_back_on_empty_groq_response(
    mock_get_client,
):
    """
    If Groq unexpectedly returns empty content, Harbor should
    safely fall back to the user's original question.
    """

    client = MagicMock()

    response = MagicMock()

    response.choices[0].message.content = ""

    client.chat.completions.create.return_value = (
        response
    )

    mock_get_client.return_value = client

    question = (
        "What if it takes longer than that?"
    )

    result = contextualize_question(
        question=question,
        history=[
            {
                "role": "user",
                "content": (
                    "How long does a refund take?"
                ),
            }
        ],
        conversation_summary=None,
    )

    assert result == question


def test_contextualizer_rejects_blank_question():
    """
    Blank questions should be rejected before Harbor performs
    any contextualization work.
    """

    with pytest.raises(
        ValueError,
        match="Question cannot be empty",
    ):
        contextualize_question(
            question="   ",
            history=[],
            conversation_summary=None,
        )