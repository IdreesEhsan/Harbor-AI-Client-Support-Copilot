import re

from app.guardrails.schemas import (
    InputGuardrailResult,
)


EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+"
    r"@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)


PHONE_PATTERN = re.compile(
    r"(?<!\w)"
    r"(?:\+?\d{1,3}[\s.-]?)?"
    r"(?:\(?\d{2,4}\)?[\s.-]?)"
    r"\d{3,4}[\s.-]?\d{3,4}"
    r"(?!\w)"
)


PASSWORD_PATTERN = re.compile(
    r"(?i)"
    r"\b(password|passwd|pwd)"
    r"\s*(?:is|=|:)\s*"
    r"([^\s,;]+)"
)


API_KEY_PATTERN = re.compile(
    r"(?i)"
    r"\b(api[\s_-]*key|secret[\s_-]*key)"
    r"\s*(?:is|=|:)\s*"
    r"([^\s,;]+)"
)


def _redact_credentials(
    content: str,
) -> tuple[str, bool]:
    """
    Redact credentials explicitly supplied by the user.

    We detect credentials using surrounding labels rather
    than treating arbitrary strings as secrets. This reduces
    false positives for normal support identifiers.
    """

    credential_found = False

    def replace_password(
        match: re.Match,
    ) -> str:
        nonlocal credential_found
        credential_found = True

        label = match.group(1)

        return (
            f"{label} is "
            "[REDACTED_CREDENTIAL]"
        )

    def replace_api_key(
        match: re.Match,
    ) -> str:
        nonlocal credential_found
        credential_found = True

        label = match.group(1)

        return (
            f"{label} is "
            "[REDACTED_CREDENTIAL]"
        )

    content = PASSWORD_PATTERN.sub(
        replace_password,
        content,
    )

    content = API_KEY_PATTERN.sub(
        replace_api_key,
        content,
    )

    return content, credential_found


def _redact_pii(
    content: str,
) -> tuple[str, bool]:
    """
    Redact common contact PII while preserving the rest of
    the support request.

    Phase 9 begins conservatively with email addresses and
    phone numbers. Additional PII types can be added later
    with dedicated tests.
    """

    pii_found = False

    def replace_email(
        match: re.Match,
    ) -> str:
        nonlocal pii_found
        pii_found = True

        return "[REDACTED_EMAIL]"

    def replace_phone(
        match: re.Match,
    ) -> str:
        nonlocal pii_found
        pii_found = True

        return "[REDACTED_PHONE]"

    content = EMAIL_PATTERN.sub(
        replace_email,
        content,
    )

    content = PHONE_PATTERN.sub(
        replace_phone,
        content,
    )

    return content, pii_found


def evaluate_input(
    content: str,
) -> InputGuardrailResult:
    """
    Evaluate and sanitize user input before normal Harbor
    agent processing.

    Credentials receive higher priority than ordinary PII.
    Normal support identifiers such as order references are
    intentionally not treated as PII.
    """

    if not isinstance(content, str):
        raise TypeError(
            "Input content must be a string."
        )

    original_length = len(content)

    if not content.strip():
        return InputGuardrailResult(
            status="block",
            category="policy_violation",
            reason="Input cannot be empty.",
            risk_level="low",
            original_length=original_length,
        )

    sanitized, credential_found = (
        _redact_credentials(content)
    )

    sanitized, pii_found = _redact_pii(
        sanitized
    )

    # Credentials have stronger security implications than
    # ordinary contact PII, so they determine the category
    # whenever both are present.
    if credential_found:
        return InputGuardrailResult(
            status="redact",
            category="credential",
            reason=(
                "Credential-like information was detected "
                "and redacted."
            ),
            risk_level="high",
            redacted_content=sanitized,
            original_length=original_length,
        )

    if pii_found:
        return InputGuardrailResult(
            status="redact",
            category="pii",
            reason=(
                "Personal information was detected "
                "and redacted."
            ),
            risk_level="medium",
            redacted_content=sanitized,
            original_length=original_length,
        )

    return InputGuardrailResult(
        status="allow",
        category="none",
        reason="No input guardrail violation detected.",
        risk_level="low",
        original_length=original_length,
    )