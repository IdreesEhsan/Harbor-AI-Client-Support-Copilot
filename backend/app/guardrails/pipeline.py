from app.guardrails.input_guardrail import (
    evaluate_input,
)
from app.guardrails.prompt_injection import (
    detect_prompt_injection,
)
from app.guardrails.schemas import (
    InputGuardrailResult,
)


def run_input_guardrails(
    content: str,
) -> InputGuardrailResult:
    """
    Run Harbor's input safety checks in security priority order.

    Prompt-injection detection runs against the original input
    before PII/credential sanitization. This prevents redaction
    from changing text before injection analysis occurs.
    """

    if not isinstance(content, str):
        raise TypeError(
            "Input content must be a string."
        )

    original_length = len(content)

    # Basic input validation belongs to the existing input
    # guardrail and should happen before normal processing.
    if not content.strip():
        return evaluate_input(content)

    injection_result = detect_prompt_injection(
        content
    )

    if injection_result.status == "block":
        return InputGuardrailResult(
            status="block",
            category="prompt_injection",
            reason=injection_result.reason,
            risk_level=injection_result.risk_level,
            original_length=original_length,
        )

    # If no injection attack was found, continue through the
    # PII and credential sanitization layer.
    return evaluate_input(content)