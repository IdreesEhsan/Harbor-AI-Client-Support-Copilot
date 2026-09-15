from typing import Literal

from pydantic import BaseModel, Field


ToolRiskLevel = Literal[
    "read",
    "analysis",
    "write",
]

ToolDecision = Literal[
    "allow",
    "block",
    "require_approval",
]


class ToolGuardrailResult(BaseModel):
    """
    Security decision made before Harbor executes a tool.
    """

    decision: ToolDecision

    tool_name: str = Field(
        min_length=1,
    )

    risk_level: ToolRiskLevel

    reason: str = Field(
        min_length=1,
        max_length=500,
    )


# ============================================================
# Harbor Tool Policy
# ============================================================

# Read-only tools retrieve information but do not modify
# application or external-system state.
READ_ONLY_TOOLS = {
    "search_knowledge_base",
    "lookup_conversation",
    "lookup_ticket_status",
}


# Analysis tools calculate or classify information but do not
# directly create external side effects.
ANALYSIS_TOOLS = {
    "classify_severity",
}


# Write tools can create or modify persistent/external state.
# These receive stronger protection.
WRITE_TOOLS = {
    "create_escalation",
    "create_ticket",
    "update_ticket",
    "send_notification",
}


def evaluate_tool_call(
    tool_name: str,
) -> ToolGuardrailResult:
    """
    Decide whether Harbor may execute a requested tool.

    Security policy:

    - Known read-only tools:
        allow

    - Known analysis tools:
        allow

    - Known write/side-effect tools:
        require human approval

    - Unknown tools:
        block

    Unknown tools fail closed so an LLM cannot invent a tool
    name and gain capabilities that Harbor never explicitly
    authorized.
    """

    if not isinstance(tool_name, str):
        raise TypeError(
            "Tool name must be a string."
        )

    tool_name = tool_name.strip()

    if not tool_name:
        return ToolGuardrailResult(
            decision="block",
            tool_name="unknown",
            risk_level="write",
            reason=(
                "Empty tool names are not allowed."
            ),
        )

    if tool_name in READ_ONLY_TOOLS:
        return ToolGuardrailResult(
            decision="allow",
            tool_name=tool_name,
            risk_level="read",
            reason=(
                "Known read-only Harbor tool."
            ),
        )

    if tool_name in ANALYSIS_TOOLS:
        return ToolGuardrailResult(
            decision="allow",
            tool_name=tool_name,
            risk_level="analysis",
            reason=(
                "Known analysis-only Harbor tool."
            ),
        )

    if tool_name in WRITE_TOOLS:
        return ToolGuardrailResult(
            decision="require_approval",
            tool_name=tool_name,
            risk_level="write",
            reason=(
                "Tool may modify persistent or external "
                "state and requires approval."
            ),
        )

    # Fail closed for anything Harbor has not explicitly
    # registered in its security policy.
    return ToolGuardrailResult(
        decision="block",
        tool_name=tool_name,
        risk_level="write",
        reason=(
            "Tool is not registered in Harbor's "
            "approved tool policy."
        ),
    )