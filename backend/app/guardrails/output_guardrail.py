import re

from app.guardrails.schemas import (
    OutputGuardrailResult,
)


# ============================================================
# Sensitive Output Patterns
# ============================================================

EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+"
    r"@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

PHONE_PATTERN = re.compile(
    r"(?<!\w)"
    r"(?:\+?\d{1,3}[\s-]?)?"
    r"(?:\d[\s-]?){9,12}"
    r"(?!\w)"
)

# Detect common credential-style output.
#
# We intentionally look for an explicit credential label.
# This reduces false positives for ordinary support text.
CREDENTIAL_PATTERN = re.compile(
    r"\b("
    r"password|"
    r"api[\s_-]*key|"
    r"access[\s_-]*token|"
    r"auth[\s_-]*token|"
    r"secret"
    r")\b"
    r"\s*(?:is|=|:)\s*"
    r"([^\s,;]+)",
    re.IGNORECASE,
)


# ============================================================
# Protected Internal-Instruction Patterns
# ============================================================

SYSTEM_PROMPT_DISCLOSURE_PATTERNS = [
    re.compile(
        r"\bmy\s+system\s+prompt\s+(?:is|says|contains)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bmy\s+hidden\s+instructions?\s+(?:are|say|include)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bmy\s+internal\s+instructions?\s+(?:are|say|include)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bhere\s+(?:is|are)\s+my\s+system\s+(?:prompt|instructions?)\b",
        re.IGNORECASE,
    ),
]


# ============================================================
# Internal Helpers
# ============================================================


def _redact_sensitive_output(
    content: str,
) -> tuple[str, str]:
    """
    Redact sensitive information from generated output.

    Returns:
        A tuple containing:
        - sanitized content
        - detected category
    """

    redacted = content
    detected_category = "none"

    # Credentials receive the strongest redaction category.
    if CREDENTIAL_PATTERN.search(redacted):
        redacted = CREDENTIAL_PATTERN.sub(
            lambda match: (
                f"{match.group(1)} is "
                "[REDACTED_CREDENTIAL]"
            ),
            redacted,
        )

        detected_category = "credential"

    # PII may coexist with credentials. We still redact it,
    # while preserving "credential" as the stronger category.
    if EMAIL_PATTERN.search(redacted):
        redacted = EMAIL_PATTERN.sub(
            "[REDACTED_EMAIL]",
            redacted,
        )

        if detected_category == "none":
            detected_category = "pii"

    if PHONE_PATTERN.search(redacted):
        redacted = PHONE_PATTERN.sub(
            "[REDACTED_PHONE]",
            redacted,
        )

        if detected_category == "none":
            detected_category = "pii"

    return redacted, detected_category


def _contains_system_prompt_disclosure(
    content: str,
) -> bool:
    """
    Detect high-confidence attempts by generated output to
    disclose Harbor's protected internal instructions.

    This intentionally uses narrow patterns to avoid blocking
    normal support discussions containing words such as
    'system' or 'instructions'.
    """

    return any(
        pattern.search(content)
        for pattern in SYSTEM_PROMPT_DISCLOSURE_PATTERNS
    )


# ============================================================
# Public Output Guardrail
# ============================================================


def evaluate_output(
    content: str,
) -> OutputGuardrailResult:
    """
    Evaluate Harbor-generated content before persistence and
    before returning it to the client.

    Policy:

    - Empty output:
        block

    - System-prompt/internal-instruction disclosure:
        block

    - Credentials:
        redact

    - Email/phone PII:
        redact

    - Normal support output:
        allow

    The output guardrail does not determine whether the answer
    is factually correct or RAG-grounded. Those responsibilities
    belong to Harbor's RAG and agent layers.
    """

    if not isinstance(content, str):
        raise TypeError(
            "Output content must be a string."
        )

    output_length = len(content)

    if not content.strip():
        return OutputGuardrailResult(
            status="block",
            category="policy_violation",
            reason=(
                "Empty assistant output is not allowed."
            ),
            risk_level="medium",
            output_length=output_length,
        )

    # Protected system/internal instructions should never be
    # returned to the user or stored as a normal assistant
    # conversation message.
    if _contains_system_prompt_disclosure(
        content
    ):
        return OutputGuardrailResult(
            status="block",
            category="prompt_injection",
            reason=(
                "Generated output appears to disclose "
                "protected internal instructions."
            ),
            risk_level="high",
            output_length=output_length,
        )

    redacted_content, category = (
        _redact_sensitive_output(
            content
        )
    )

    if category == "credential":
        return OutputGuardrailResult(
            status="redact",
            category="credential",
            reason=(
                "Credential-like information was removed "
                "from generated output."
            ),
            risk_level="high",
            redacted_content=redacted_content,
            output_length=output_length,
        )

    if category == "pii":
        return OutputGuardrailResult(
            status="redact",
            category="pii",
            reason=(
                "Personally identifiable information was "
                "removed from generated output."
            ),
            risk_level="medium",
            redacted_content=redacted_content,
            output_length=output_length,
        )

    return OutputGuardrailResult(
        status="allow",
        category="none",
        reason=(
            "Generated output passed Harbor's output "
            "guardrails."
        ),
        risk_level="low",
        output_length=output_length,
    )