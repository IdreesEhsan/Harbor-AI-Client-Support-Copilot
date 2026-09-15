from unittest.mock import MagicMock, patch

import pytest

from app.agent.tools import (
    ToolApprovalRequiredError,
    ToolExecutionBlockedError,
    authorize_approved_tool_execution,
    authorize_tool_execution,
    search_knowledge_base,
)


def test_authorize_allows_search_knowledge_base():
    """
    Harbor's real knowledge-base tool is registered as a
    permitted read-only capability.
    """

    # No exception means authorization succeeded.
    authorize_tool_execution(
        "search_knowledge_base"
    )


def test_authorize_blocks_unknown_tool():
    """
    Unknown capabilities must fail before execution.
    """

    with pytest.raises(
        ToolExecutionBlockedError,
        match="not authorized",
    ):
        authorize_tool_execution(
            "export_customer_database"
        )


def test_authorize_requires_approval_for_write_tool():
    """
    Side-effecting tools must not execute automatically.
    """

    with pytest.raises(
        ToolApprovalRequiredError,
        match="requires human approval",
    ):
        authorize_tool_execution(
            "create_escalation"
        )


@patch(
    "app.agent.tools.answer_question"
)
def test_search_knowledge_base_executes_after_authorization(
    mock_answer_question,
):
    """
    The real LangChain knowledge-base tool should execute its
    underlying RAG capability after authorization succeeds.
    """

    rag_result = MagicMock()

    rag_result.model_dump.return_value = {
        "answer": (
            "Refunds normally take "
            "5 to 10 business days."
        ),
        "citations": [],
    }

    mock_answer_question.return_value = (
        rag_result
    )

    result = search_knowledge_base.invoke(
        {
            "question": (
                "How long does a refund take?"
            )
        }
    )

    mock_answer_question.assert_called_once_with(
        question=(
            "How long does a refund take?"
        )
    )

    assert result == {
        "answer": (
            "Refunds normally take "
            "5 to 10 business days."
        ),
        "citations": [],
    }


@patch(
    "app.agent.tools.answer_question"
)
@patch(
    "app.agent.tools.evaluate_tool_call"
)
def test_blocked_tool_does_not_execute_rag(
    mock_evaluate,
    mock_answer_question,
):
    """
    If authorization rejects the knowledge-base tool, its
    underlying RAG capability must never execute.
    """

    decision = MagicMock()
    decision.decision = "block"

    mock_evaluate.return_value = decision

    with pytest.raises(
        ToolExecutionBlockedError
    ):
        search_knowledge_base.invoke(
            {
                "question": (
                    "How long does a refund take?"
                )
            }
        )

    # Authorization failed before the underlying capability
    # had any opportunity to execute.
    mock_answer_question.assert_not_called()


@patch(
    "app.agent.tools.answer_question"
)
@patch(
    "app.agent.tools.evaluate_tool_call"
)
def test_approval_required_tool_does_not_execute_rag(
    mock_evaluate,
    mock_answer_question,
):
    """
    An approval-required decision must stop execution just as
    strictly as a blocked decision.
    """

    decision = MagicMock()
    decision.decision = "require_approval"

    mock_evaluate.return_value = decision

    with pytest.raises(
        ToolApprovalRequiredError
    ):
        search_knowledge_base.invoke(
            {
                "question": (
                    "How long does a refund take?"
                )
            }
        )

    mock_answer_question.assert_not_called()


@patch(
    "app.agent.tools.evaluate_tool_call"
)
def test_unexpected_authorization_decision_fails_closed(
    mock_evaluate,
):
    """
    Unexpected policy states must never default to allowing
    execution.
    """

    decision = MagicMock()

    decision.decision = (
        "something_unexpected"
    )

    mock_evaluate.return_value = decision

    with pytest.raises(
        ToolExecutionBlockedError,
        match="unsupported authorization decision",
    ):
        authorize_tool_execution(
            "search_knowledge_base"
        )


def test_approved_write_tool_can_execute():
    """
    A registered write tool may cross the approval-aware
    authorization boundary after persisted human approval.
    """

    # No exception means the specific write capability has
    # been authorized for execution.
    authorize_approved_tool_execution(
        "create_escalation",
        approval_status="approved",
    )


def test_pending_write_tool_cannot_execute():
    """
    A ticket whose human decision is still pending must not
    authorize an external side effect.
    """

    with pytest.raises(
        ToolApprovalRequiredError,
        match=(
            "requires approved human authorization"
        ),
    ):
        authorize_approved_tool_execution(
            "create_escalation",
            approval_status="pending",
        )


def test_rejected_write_tool_cannot_execute():
    """
    Human rejection must prevent the associated write
    capability from executing.
    """

    with pytest.raises(
        ToolApprovalRequiredError,
        match=(
            "requires approved human authorization"
        ),
    ):
        authorize_approved_tool_execution(
            "create_escalation",
            approval_status="rejected",
        )


def test_unknown_tool_stays_blocked_even_when_approved():
    """
    Human approval cannot authorize a capability that is not
    registered in Harbor's centralized tool policy.
    """

    with pytest.raises(
        ToolExecutionBlockedError,
        match="not authorized",
    ):
        authorize_approved_tool_execution(
            "delete_everything",
            approval_status="approved",
        )


def test_read_tool_remains_allowed_without_approval():
    """
    Read-only tools remain executable without requiring the
    human approval workflow.

    The approval status is irrelevant because the centralized
    tool policy already classifies this capability as safe to
    execute directly.
    """

    authorize_approved_tool_execution(
        "search_knowledge_base",
        approval_status="pending",
    )


def test_create_escalation_still_requires_normal_approval_boundary():
    """
    The original authorization boundary must continue to
    reject direct execution of a write tool.

    Callers therefore cannot bypass HITL by invoking the
    normal authorization function instead of the
    approval-aware execution boundary.
    """

    with pytest.raises(
        ToolApprovalRequiredError,
        match="requires human approval",
    ):
        authorize_tool_execution(
            "create_escalation"
        )