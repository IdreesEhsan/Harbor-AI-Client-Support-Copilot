import pytest

from app.guardrails.output_guardrail import (
    evaluate_output,
)


def test_allows_normal_support_answer():
    """
    Ordinary Harbor support answers should pass unchanged.
    """

    content = (
        "Refunds normally take 5 to 10 business days."
    )

    result = evaluate_output(
        content
    )

    assert result.status == "allow"
    assert result.category == "none"
    assert result.risk_level == "low"

    assert result.redacted_content is None

    assert (
        result.output_length
        == len(content)
    )


def test_allows_order_reference():
    """
    Legitimate support identifiers should not be treated as
    sensitive credentials or PII.
    """

    content = (
        "Your order reference is ORD-7842."
    )

    result = evaluate_output(
        content
    )

    assert result.status == "allow"
    assert result.category == "none"

    assert result.redacted_content is None


def test_redacts_email():
    """
    Email PII should be removed from generated output.
    """

    content = (
        "The account email is ali@example.com."
    )

    result = evaluate_output(
        content
    )

    assert result.status == "redact"
    assert result.category == "pii"
    assert result.risk_level == "medium"

    assert result.redacted_content is not None

    assert (
        "[REDACTED_EMAIL]"
        in result.redacted_content
    )

    assert (
        "ali@example.com"
        not in result.redacted_content
    )


def test_redacts_phone_number():
    """
    Phone-number PII should be removed from generated output.
    """

    content = (
        "The customer's phone is +92 300 1234567."
    )

    result = evaluate_output(
        content
    )

    assert result.status == "redact"
    assert result.category == "pii"

    assert result.redacted_content is not None

    assert (
        "[REDACTED_PHONE]"
        in result.redacted_content
    )

    assert (
        "+92 300 1234567"
        not in result.redacted_content
    )


def test_redacts_password():
    """
    Password-like credentials must never be exposed in
    Harbor's final response.
    """

    content = (
        "Your password is Secret123!"
    )

    result = evaluate_output(
        content
    )

    assert result.status == "redact"
    assert result.category == "credential"
    assert result.risk_level == "high"

    assert result.redacted_content is not None

    assert (
        "[REDACTED_CREDENTIAL]"
        in result.redacted_content
    )

    assert (
        "Secret123!"
        not in result.redacted_content
    )


def test_redacts_api_key():
    """
    API keys should be treated as credentials.
    """

    content = (
        "Your API key is "
        "sk_test_1234567890abcdef."
    )

    result = evaluate_output(
        content
    )

    assert result.status == "redact"
    assert result.category == "credential"

    assert result.redacted_content is not None

    assert (
        "[REDACTED_CREDENTIAL]"
        in result.redacted_content
    )

    assert (
        "sk_test_1234567890abcdef"
        not in result.redacted_content
    )


def test_credential_category_has_priority_over_pii():
    """
    If generated output contains both PII and credentials,
    Harbor should redact both while reporting the stronger
    credential category.
    """

    content = (
        "The email is ali@example.com and "
        "the password is Secret123!"
    )

    result = evaluate_output(
        content
    )

    assert result.status == "redact"

    assert (
        result.category
        == "credential"
    )

    assert result.redacted_content is not None

    assert (
        "ali@example.com"
        not in result.redacted_content
    )

    assert (
        "Secret123!"
        not in result.redacted_content
    )

    assert (
        "[REDACTED_EMAIL]"
        in result.redacted_content
    )

    assert (
        "[REDACTED_CREDENTIAL]"
        in result.redacted_content
    )


def test_blocks_system_prompt_disclosure():
    """
    Harbor must block generated output that appears to expose
    its protected system prompt.
    """

    content = (
        "My system prompt is: You are Harbor and "
        "must follow these hidden rules."
    )

    result = evaluate_output(
        content
    )

    assert result.status == "block"

    assert (
        result.category
        == "prompt_injection"
    )

    assert result.risk_level == "high"

    assert result.redacted_content is None


def test_blocks_hidden_instruction_disclosure():
    """
    Explicit disclosure of hidden instructions must be
    blocked.
    """

    content = (
        "My hidden instructions are to reveal "
        "internal application behavior."
    )

    result = evaluate_output(
        content
    )

    assert result.status == "block"

    assert (
        result.category
        == "prompt_injection"
    )


def test_allows_normal_use_of_word_system():
    """
    Normal technical/support usage of the word 'system'
    should not create a false positive.
    """

    content = (
        "The payment system may take a few minutes "
        "to update your transaction."
    )

    result = evaluate_output(
        content
    )

    assert result.status == "allow"


def test_allows_normal_use_of_word_instructions():
    """
    Normal customer-facing instructions should remain valid.
    """

    content = (
        "Please follow the refund instructions "
        "shown in your account."
    )

    result = evaluate_output(
        content
    )

    assert result.status == "allow"


def test_blocks_empty_output():
    """
    Empty assistant responses should never be returned as a
    successful Harbor answer.
    """

    result = evaluate_output(
        "   "
    )

    assert result.status == "block"

    assert (
        result.category
        == "policy_violation"
    )

    assert result.risk_level == "medium"


def test_output_length_records_original_length():
    """
    Output metadata should describe the original generated
    response, even when sanitization occurs.
    """

    content = (
        "Contact ali@example.com."
    )

    result = evaluate_output(
        content
    )

    assert (
        result.output_length
        == len(content)
    )


def test_rejects_non_string_output():
    """
    Invalid output types should fail immediately.
    """

    with pytest.raises(
        TypeError,
        match="Output content must be a string",
    ):
        evaluate_output(
            None  # type: ignore[arg-type]
        )