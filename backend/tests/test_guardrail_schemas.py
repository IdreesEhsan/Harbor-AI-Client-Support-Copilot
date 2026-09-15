import pytest
from pydantic import ValidationError

from app.guardrails.schemas import (
    GuardrailResult,
    InputGuardrailResult,
    OutputGuardrailResult,
)


def test_guardrail_result_allows_safe_request():
    """
    A normal guardrail result should represent an allowed,
    low-risk request.
    """

    result = GuardrailResult(
        status="allow",
        category="none",
        reason="No guardrail violation detected.",
        risk_level="low",
    )

    assert result.status == "allow"
    assert result.category == "none"
    assert result.risk_level == "low"
    assert result.redacted_content is None


def test_guardrail_result_supports_redaction():
    """
    Guardrails should be able to return sanitized content
    without blocking the entire request.
    """

    result = GuardrailResult(
        status="redact",
        category="pii",
        reason="Sensitive information was detected.",
        risk_level="medium",
        redacted_content=(
            "My email is [REDACTED_EMAIL]."
        ),
    )

    assert result.status == "redact"
    assert result.category == "pii"

    assert result.redacted_content == (
        "My email is [REDACTED_EMAIL]."
    )


def test_guardrail_result_supports_credential_category():
    """
    Credentials are modeled separately from ordinary PII
    because they require stronger protection.
    """

    result = GuardrailResult(
        status="redact",
        category="credential",
        reason="A credential was detected.",
        risk_level="high",
        redacted_content="[REDACTED_CREDENTIAL]",
    )

    assert result.category == "credential"
    assert result.risk_level == "high"


def test_input_guardrail_tracks_original_length():
    """
    Input diagnostics should be possible without requiring
    the raw user input to be stored in logs.
    """

    result = InputGuardrailResult(
        status="allow",
        category="none",
        reason="Input is safe.",
        risk_level="low",
        original_length=42,
    )

    assert result.original_length == 42


def test_output_guardrail_tracks_output_length():
    """
    Output guardrails should record response length for
    future diagnostics and observability.
    """

    result = OutputGuardrailResult(
        status="allow",
        category="none",
        reason="Output is safe.",
        risk_level="low",
        output_length=120,
    )

    assert result.output_length == 120


def test_invalid_guardrail_status_is_rejected():
    """
    Unknown status values must fail validation instead of
    silently entering the agent workflow.
    """

    with pytest.raises(ValidationError):
        GuardrailResult(
            status="ignore",
            category="none",
            reason="Invalid status.",
            risk_level="low",
        )


def test_invalid_guardrail_category_is_rejected():
    """
    Unknown categories should fail closed at the schema
    boundary.
    """

    with pytest.raises(ValidationError):
        GuardrailResult(
            status="block",
            category="unknown",
            reason="Invalid category.",
            risk_level="high",
        )


def test_invalid_risk_level_is_rejected():
    """
    Risk levels are constrained to Harbor's approved
    vocabulary.
    """

    with pytest.raises(ValidationError):
        GuardrailResult(
            status="block",
            category="policy_violation",
            reason="Invalid risk level.",
            risk_level="extreme",
        )


def test_negative_input_length_is_rejected():
    """
    Input length cannot logically be negative.
    """

    with pytest.raises(ValidationError):
        InputGuardrailResult(
            status="allow",
            category="none",
            reason="Input is safe.",
            risk_level="low",
            original_length=-1,
        )


def test_empty_reason_is_rejected():
    """
    Every guardrail decision must explain why it was made.
    """

    with pytest.raises(ValidationError):
        GuardrailResult(
            status="allow",
            category="none",
            reason="",
            risk_level="low",
        )