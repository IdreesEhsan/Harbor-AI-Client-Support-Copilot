from app.agent.nodes import (
    pending_approval_node,
    tool_authorization_node,
)


def test_read_tool_is_authorized():
    """
    Read-only tools should be allowed without human
    approval.
    """

    state = {
        "pending_tool_name": (
            "search_knowledge_base"
        ),
    }

    result = tool_authorization_node(
        state
    )

    assert (
        result["tool_decision"]
        == "allow"
    )

    assert (
        "read-only"
        in result["tool_decision_reason"]
    )


def test_write_tool_requires_approval():
    """
    Side-effecting tools should be marked as requiring
    explicit human approval.
    """

    state = {
        "pending_tool_name": (
            "create_escalation"
        ),
    }

    result = tool_authorization_node(
        state
    )

    assert (
        result["tool_decision"]
        == "require_approval"
    )

    assert (
        "requires approval"
        in result["tool_decision_reason"]
    )


def test_unknown_tool_is_blocked():
    """
    Unknown capabilities must fail closed.
    """

    state = {
        "pending_tool_name": (
            "delete_customer_database"
        ),
    }

    result = tool_authorization_node(
        state
    )

    assert (
        result["tool_decision"]
        == "block"
    )


def test_pending_approval_sets_pending_state():
    """
    Approval-required operations should stop in a pending
    state instead of executing automatically.
    """

    state = {
        "pending_tool_name": (
            "create_escalation"
        ),
        "severity": "high",
    }

    result = pending_approval_node(
        state
    )

    assert (
        result["pending_human_approval"]
        is True
    )

    assert (
        result["approval_status"]
        == "pending"
    )

    assert (
        result["escalation_required"]
        is True
    )

    assert (
        result["action"]
        == "escalate"
    )


def test_pending_approval_preserves_severity():
    """
    Existing agent severity should survive the transition
    into human approval.
    """

    state = {
        "pending_tool_name": (
            "create_ticket"
        ),
        "severity": "critical",
    }

    result = pending_approval_node(
        state
    )

    assert (
        result["severity"]
        == "critical"
    )


def test_pending_approval_has_no_citations():
    """
    Human-approval status is workflow information rather
    than a knowledge-base answer, so it must not produce
    fake RAG citations.
    """

    state = {
        "pending_tool_name": (
            "create_escalation"
        ),
    }

    result = pending_approval_node(
        state
    )

    assert result["citations"] == []

    assert (
        result["grounded"]
        is False
    )


def test_pending_approval_does_not_claim_execution():
    """
    Harbor's response must clearly state that approval is
    still required rather than claiming the requested action
    has already happened.
    """

    state = {
        "pending_tool_name": (
            "create_escalation"
        ),
    }

    result = pending_approval_node(
        state
    )

    answer = result[
        "answer"
    ].lower()

    assert (
        "requires human approval"
        in answer
    )

    assert (
        "created successfully"
        not in answer
    )

    assert (
        "completed successfully"
        not in answer
    )