from langchain_core.tools import tool

from app.guardrails.tool_guardrail import (
    evaluate_tool_call,
)
from app.rag.service import answer_question


class ToolExecutionBlockedError(Exception):
    """
    Raised when Harbor's security policy refuses to execute
    a requested tool.
    """


class ToolApprovalRequiredError(Exception):
    """
    Raised when a side-effecting tool requires explicit
    human approval before execution.
    """


class ToolApprovalInvalidError(Exception):
    """
    Raised when Harbor is told that approval exists but the
    supplied approval state is not valid for execution.

    This prevents callers from bypassing the approval
    workflow with arbitrary truthy values.
    """


def authorize_tool_execution(
    tool_name: str,
) -> None:
    """
    Authorize a tool that does not require human approval.

    Read-only and analysis tools may execute when the
    centralized tool policy returns ``allow``.

    Write tools continue to raise ToolApprovalRequiredError.
    They must use authorize_approved_tool_execution() after
    persisted human approval has been verified.
    """

    decision = evaluate_tool_call(
        tool_name
    )

    if decision.decision == "allow":
        return

    if decision.decision == "require_approval":
        raise ToolApprovalRequiredError(
            f"Tool '{tool_name}' requires human approval."
        )

    if decision.decision == "block":
        raise ToolExecutionBlockedError(
            f"Tool '{tool_name}' is not authorized."
        )

    # Fail closed if the policy contract changes in an
    # unexpected way.
    raise ToolExecutionBlockedError(
        f"Tool '{tool_name}' returned an unsupported "
        "authorization decision."
    )


def authorize_approved_tool_execution(
    tool_name: str,
    *,
    approval_status: str,
) -> None:
    """
    Authorize execution of a tool after persisted human
    approval has been verified.

    This function does not itself decide whether a human
    approved the action. The caller must load the persisted
    approval state from Harbor's trusted ticket storage and
    pass that state here.

    Security rules:

    - normally allowed tools remain allowed;
    - approval-required tools execute only when the persisted
      approval status is exactly ``approved``;
    - rejected or pending approvals cannot execute;
    - unknown/blocked tools remain blocked even if someone
      supplies ``approved``.
    """

    decision = evaluate_tool_call(
        tool_name
    )

    if decision.decision == "allow":
        return

    if decision.decision == "block":
        raise ToolExecutionBlockedError(
            f"Tool '{tool_name}' is not authorized."
        )

    if decision.decision == "require_approval":
        if approval_status != "approved":
            raise ToolApprovalRequiredError(
                f"Tool '{tool_name}' requires approved "
                "human authorization before execution."
            )

        return

    # Defensive fail-closed behavior.
    raise ToolExecutionBlockedError(
        f"Tool '{tool_name}' returned an unsupported "
        "authorization decision."
    )


@tool
def search_knowledge_base(
    question: str,
) -> dict:
    """
    Search Harbor's knowledge base and generate a grounded
    answer.

    Use this tool for normal customer-support questions that
    may be answered using Harbor's indexed knowledge-base
    documents.

    This operation is read-only, but it still passes through
    Harbor's centralized authorization boundary.
    """

    authorize_tool_execution(
        "search_knowledge_base"
    )

    result = answer_question(
        question=question
    )

    return result.model_dump()