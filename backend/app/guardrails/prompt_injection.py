import re

from app.guardrails.schemas import GuardrailResult


# High-confidence patterns focus on attempts to manipulate
# Harbor's instruction hierarchy rather than ordinary uses
# of words such as "prompt", "system", or "instructions".
INJECTION_PATTERNS = [
    re.compile(
        r"\bignore\s+(?:all\s+)?(?:previous|prior|system)"
        r"\s+(?:instructions?|prompts?|rules?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:reveal|show|display|print|expose)"
        r"\s+(?:your\s+)?(?:system\s+prompt|hidden\s+instructions?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:override|bypass|disable)"
        r"\s+(?:your\s+)?(?:instructions?|rules?|guardrails?|safety)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bforget\s+(?:all\s+)?(?:your\s+)?"
        r"(?:instructions?|rules?|constraints?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bignore\s+(?:the\s+)?retrieved\s+context\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\btreat\s+(?:this|user|conversation)"
        r"\s+(?:content|message|history)"
        r"\s+as\s+(?:a\s+)?system\s+(?:prompt|instruction)\b",
        re.IGNORECASE,
    ),
]


def detect_prompt_injection(
    content: str,
) -> GuardrailResult:
    """
    Detect high-confidence prompt-injection attempts.

    This detector intentionally uses narrow patterns to avoid
    blocking legitimate support questions that happen to use
    words such as "instructions", "system", or "prompt".
    """

    if not isinstance(content, str):
        raise TypeError(
            "Prompt-injection input must be a string."
        )

    if not content.strip():
        return GuardrailResult(
            status="allow",
            category="none",
            reason="No prompt-injection attempt detected.",
            risk_level="low",
        )

    for pattern in INJECTION_PATTERNS:
        if pattern.search(content):
            return GuardrailResult(
                status="block",
                category="prompt_injection",
                reason=(
                    "The input contains an attempt to "
                    "override or expose Harbor's protected "
                    "instructions."
                ),
                risk_level="high",
            )

    return GuardrailResult(
        status="allow",
        category="none",
        reason="No prompt-injection attempt detected.",
        risk_level="low",
    )