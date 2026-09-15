import pytest

from app.guardrails.input_guardrail import (
    evaluate_input,
)


def test_normal_support_question_is_allowed():
    result = evaluate_input(
        "How long does a refund normally take?"
    )

    assert result.status == "allow"
    assert result.category == "none"
    assert result.redacted_content is None


def test_order_reference_is_not_redacted():
    """
    Customer support identifiers are useful conversational
    context and should not automatically be classified as PII.
    """

    message = (
        "My order reference is ORD-7842."
    )

    result = evaluate_input(
        message
    )

    assert result.status == "allow"
    assert result.category == "none"
    assert result.redacted_content is None


def test_email_is_redacted():
    result = evaluate_input(
        "My email is ali@example.com."
    )

    assert result.status == "redact"
    assert result.category == "pii"
    assert result.risk_level == "medium"

    assert (
        "[REDACTED_EMAIL]"
        in result.redacted_content
    )

    assert (
        "ali@example.com"
        not in result.redacted_content
    )


def test_phone_number_is_redacted():
    result = evaluate_input(
        "Call me at +92 300 1234567."
    )

    assert result.status == "redact"
    assert result.category == "pii"

    assert (
        "[REDACTED_PHONE]"
        in result.redacted_content
    )


def test_password_is_redacted():
    result = evaluate_input(
        "My password is hunter123."
    )

    assert result.status == "redact"
    assert result.category == "credential"
    assert result.risk_level == "high"

    assert (
        "[REDACTED_CREDENTIAL]"
        in result.redacted_content
    )

    assert (
        "hunter123"
        not in result.redacted_content
    )


def test_api_key_is_redacted():
    result = evaluate_input(
        "My API key is abc123secret."
    )

    assert result.status == "redact"
    assert result.category == "credential"

    assert (
        "[REDACTED_CREDENTIAL]"
        in result.redacted_content
    )

    assert (
        "abc123secret"
        not in result.redacted_content
    )


def test_email_and_password_are_both_redacted():
    """
    When multiple sensitive values exist, all should be
    sanitized while credentials determine the final category.
    """

    result = evaluate_input(
        "My email is ali@example.com "
        "and password is hunter123."
    )

    assert result.status == "redact"
    assert result.category == "credential"

    assert (
        "[REDACTED_EMAIL]"
        in result.redacted_content
    )

    assert (
        "[REDACTED_CREDENTIAL]"
        in result.redacted_content
    )

    assert (
        "ali@example.com"
        not in result.redacted_content
    )

    assert (
        "hunter123"
        not in result.redacted_content
    )


def test_empty_input_is_blocked():
    result = evaluate_input(
        "   "
    )

    assert result.status == "block"

    assert (
        result.category
        == "policy_violation"
    )


def test_original_length_is_recorded():
    message = "Where is my refund?"

    result = evaluate_input(
        message
    )

    assert (
        result.original_length
        == len(message)
    )


def test_non_string_input_is_rejected():
    with pytest.raises(
        TypeError,
        match="Input content must be a string",
    ):
        evaluate_input(
            12345
        )