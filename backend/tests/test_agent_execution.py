import pytest

from app.agent.execution import (
    controlled_node,
)
from app.guardrails.execution_control import (
    ExecutionLimitExceededError,
)


def test_controlled_node_increments_step_count():
    """
    A controlled node should consume exactly one graph step.
    """

    def example_node(state):
        return {
            "answer": "Hello",
        }

    wrapped = controlled_node(
        example_node
    )

    result = wrapped(
        {
            "step_count": 3,
        }
    )

    assert result["step_count"] == 4
    assert result["answer"] == "Hello"


def test_controlled_node_starts_at_zero():
    """
    Missing execution state should safely initialize at zero.
    """

    def example_node(state):
        return {
            "answer": "Hello",
        }

    wrapped = controlled_node(
        example_node
    )

    result = wrapped({})

    assert result["step_count"] == 1


def test_controlled_node_allows_twelfth_step():
    """
    Harbor's configured maximum step itself should execute.
    """

    executed = False

    def example_node(state):
        nonlocal executed

        executed = True

        return {
            "answer": "Allowed",
        }

    wrapped = controlled_node(
        example_node
    )

    result = wrapped(
        {
            "step_count": 11,
        }
    )

    assert result["step_count"] == 12
    assert executed is True


def test_controlled_node_blocks_thirteenth_step():
    """
    A node that would exceed the maximum step count must
    never execute.
    """

    executed = False

    def example_node(state):
        nonlocal executed

        executed = True

        return {
            "answer": "Should never happen",
        }

    wrapped = controlled_node(
        example_node
    )

    with pytest.raises(
        ExecutionLimitExceededError
    ):
        wrapped(
            {
                "step_count": 12,
            }
        )

    # Critical security property:
    # protected node logic never executed.
    assert executed is False


def test_controlled_node_preserves_existing_result():
    """
    Execution control should add its counter without removing
    the underlying node's state updates.
    """

    def example_node(state):
        return {
            "action": "answer",
            "grounded": True,
            "citations": [
                {
                    "source": "policy.txt",
                }
            ],
        }

    wrapped = controlled_node(
        example_node
    )

    result = wrapped(
        {
            "step_count": 4,
        }
    )

    assert result["step_count"] == 5
    assert result["action"] == "answer"
    assert result["grounded"] is True

    assert result["citations"] == [
        {
            "source": "policy.txt",
        }
    ]


def test_controlled_node_does_not_mutate_original_result():
    """
    The wrapper should create its own state update rather
    than mutating the node's original dictionary.
    """

    original_result = {
        "answer": "Safe response",
    }

    def example_node(state):
        return original_result

    wrapped = controlled_node(
        example_node
    )

    result = wrapped({})

    assert result["step_count"] == 1

    # The dictionary returned by example_node remains
    # unchanged.
    assert "step_count" not in original_result


def test_controlled_node_preserves_function_identity():
    """
    Wrapped nodes should retain meaningful names for traces
    and debugging.
    """

    def example_node(state):
        return {}

    wrapped = controlled_node(
        example_node
    )

    assert (
        wrapped.__name__
        == "controlled_example_node"
    )