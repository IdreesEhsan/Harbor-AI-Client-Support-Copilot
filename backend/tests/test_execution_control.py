import pytest

from app.guardrails.execution_control import (
    DEFAULT_EXECUTION_LIMITS,
    ExecutionLimitExceededError,
    ExecutionLimits,
    increment_step_count,
    increment_tool_call_count,
    validate_execution_counts,
)


def test_default_execution_limits():
    """
    Harbor should have conservative default limits for a
    single agent run.
    """

    assert (
        DEFAULT_EXECUTION_LIMITS.max_steps
        == 12
    )

    assert (
        DEFAULT_EXECUTION_LIMITS.max_tool_calls
        == 5
    )


def test_valid_execution_counts_are_allowed():
    """
    Normal execution counts should pass validation.
    """

    validate_execution_counts(
        step_count=3,
        tool_call_count=1,
    )


def test_exact_step_limit_is_allowed():
    """
    Reaching the configured maximum is valid.
    """

    validate_execution_counts(
        step_count=12,
        tool_call_count=0,
    )


def test_step_limit_exceeded_is_blocked():
    """
    Harbor must fail once the maximum step count has been
    exceeded.
    """

    with pytest.raises(
        ExecutionLimitExceededError,
        match="maximum allowed agent steps",
    ):
        validate_execution_counts(
            step_count=13,
            tool_call_count=0,
        )


def test_exact_tool_limit_is_allowed():
    """
    Reaching the configured tool-call maximum is valid.
    """

    validate_execution_counts(
        step_count=0,
        tool_call_count=5,
    )


def test_tool_limit_exceeded_is_blocked():
    """
    Harbor must stop excessive tool execution.
    """

    with pytest.raises(
        ExecutionLimitExceededError,
        match="maximum allowed tool calls",
    ):
        validate_execution_counts(
            step_count=0,
            tool_call_count=6,
        )


def test_increment_step_count():
    """
    Step counting should return the incremented value.
    """

    result = increment_step_count(
        4
    )

    assert result == 5


def test_increment_step_count_enforces_limit():
    """
    Incrementing beyond the step limit must fail.
    """

    with pytest.raises(
        ExecutionLimitExceededError
    ):
        increment_step_count(
            12
        )


def test_increment_tool_call_count():
    """
    Tool counting should return the incremented value.
    """

    result = increment_tool_call_count(
        2
    )

    assert result == 3


def test_increment_tool_count_enforces_limit():
    """
    Incrementing beyond the tool limit must fail.
    """

    with pytest.raises(
        ExecutionLimitExceededError
    ):
        increment_tool_call_count(
            5
        )


def test_custom_limits_are_supported():
    """
    Future workflows may define stricter execution limits.
    """

    limits = ExecutionLimits(
        max_steps=3,
        max_tool_calls=2,
    )

    validate_execution_counts(
        step_count=3,
        tool_call_count=2,
        limits=limits,
    )

    with pytest.raises(
        ExecutionLimitExceededError
    ):
        validate_execution_counts(
            step_count=4,
            tool_call_count=2,
            limits=limits,
        )


def test_negative_step_count_is_rejected():
    """
    Corrupted negative counters must not be accepted.
    """

    with pytest.raises(
        ValueError,
        match="step_count cannot be negative",
    ):
        validate_execution_counts(
            step_count=-1,
            tool_call_count=0,
        )


def test_negative_tool_count_is_rejected():
    """
    Corrupted negative tool counters must not be accepted.
    """

    with pytest.raises(
        ValueError,
        match="tool_call_count cannot be negative",
    ):
        validate_execution_counts(
            step_count=0,
            tool_call_count=-1,
        )


def test_non_integer_step_count_is_rejected():
    """
    Execution counters must use predictable integer values.
    """

    with pytest.raises(
        TypeError,
        match="step_count must be an integer",
    ):
        validate_execution_counts(
            step_count="1",  # type: ignore[arg-type]
            tool_call_count=0,
        )


def test_non_integer_tool_count_is_rejected():
    """
    Tool counters must use predictable integer values.
    """

    with pytest.raises(
        TypeError,
        match="tool_call_count must be an integer",
    ):
        validate_execution_counts(
            step_count=0,
            tool_call_count="1",  # type: ignore[arg-type]
        )