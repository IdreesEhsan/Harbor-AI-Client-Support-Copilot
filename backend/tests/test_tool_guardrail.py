import pytest

from app.guardrails.tool_guardrail import (
    evaluate_tool_call,
)


def test_allows_search_knowledge_base():
    """
    Knowledge-base search is read-only and should execute
    without human approval.
    """

    result = evaluate_tool_call(
        "search_knowledge_base"
    )

    assert result.decision == "allow"

    assert (
        result.tool_name
        == "search_knowledge_base"
    )

    assert result.risk_level == "read"


def test_allows_lookup_conversation():
    """
    Conversation lookup is classified as read-only.
    """

    result = evaluate_tool_call(
        "lookup_conversation"
    )

    assert result.decision == "allow"
    assert result.risk_level == "read"


def test_allows_lookup_ticket_status():
    """
    Reading ticket status does not modify external state.
    """

    result = evaluate_tool_call(
        "lookup_ticket_status"
    )

    assert result.decision == "allow"
    assert result.risk_level == "read"


def test_allows_severity_classification():
    """
    Severity classification performs analysis but does not
    directly modify application state.
    """

    result = evaluate_tool_call(
        "classify_severity"
    )

    assert result.decision == "allow"

    assert (
        result.risk_level
        == "analysis"
    )


def test_escalation_requires_approval():
    """
    Creating an escalation is a side-effecting operation and
    must not execute automatically.
    """

    result = evaluate_tool_call(
        "create_escalation"
    )

    assert (
        result.decision
        == "require_approval"
    )

    assert result.risk_level == "write"


def test_ticket_creation_requires_approval():
    """
    Creating an external ticket changes persistent state.
    """

    result = evaluate_tool_call(
        "create_ticket"
    )

    assert (
        result.decision
        == "require_approval"
    )

    assert result.risk_level == "write"


def test_ticket_update_requires_approval():
    """
    Updating a ticket must not execute without authorization.
    """

    result = evaluate_tool_call(
        "update_ticket"
    )

    assert (
        result.decision
        == "require_approval"
    )


def test_notification_requires_approval():
    """
    Sending a notification creates an external side effect.
    """

    result = evaluate_tool_call(
        "send_notification"
    )

    assert (
        result.decision
        == "require_approval"
    )


def test_unknown_tool_is_blocked():
    """
    Unknown tools must fail closed.
    """

    result = evaluate_tool_call(
        "delete_everything"
    )

    assert result.decision == "block"

    assert (
        result.tool_name
        == "delete_everything"
    )

    assert result.risk_level == "write"


def test_invented_llm_tool_is_blocked():
    """
    An LLM cannot gain capabilities by inventing a new tool
    name.
    """

    result = evaluate_tool_call(
        "export_customer_database"
    )

    assert result.decision == "block"


def test_empty_tool_name_is_blocked():
    """
    Empty tool names are invalid and fail closed.
    """

    result = evaluate_tool_call(
        "   "
    )

    assert result.decision == "block"

    assert (
        result.tool_name
        == "unknown"
    )


def test_tool_name_matching_is_explicit():
    """
    Similar-looking names must not inherit permissions from
    an approved tool.
    """

    result = evaluate_tool_call(
        "search_knowledge_base_admin"
    )

    assert result.decision == "block"


def test_rejects_non_string_tool_name():
    """
    Invalid tool-name types should fail immediately.
    """

    with pytest.raises(
        TypeError,
        match="Tool name must be a string",
    ):
        evaluate_tool_call(
            None  # type: ignore[arg-type]
        )