from dataclasses import dataclass


class ExecutionLimitExceededError(Exception):
    """
    Raised when Harbor exceeds an explicitly configured
    execution safety limit.
    """


@dataclass(frozen=True)
class ExecutionLimits:
    """
    Central safety limits for a single Harbor agent run.

    These limits prevent future agent workflows from
    performing uncontrolled reasoning or tool execution.
    """

    max_steps: int = 12
    max_tool_calls: int = 5


DEFAULT_EXECUTION_LIMITS = ExecutionLimits()


def validate_execution_counts(
    *,
    step_count: int,
    tool_call_count: int,
    limits: ExecutionLimits = DEFAULT_EXECUTION_LIMITS,
) -> None:
    """
    Validate the current execution counters.

    Harbor fails closed when either the graph-step limit or
    tool-call limit has been exceeded.
    """

    if not isinstance(step_count, int):
        raise TypeError(
            "step_count must be an integer."
        )

    if not isinstance(tool_call_count, int):
        raise TypeError(
            "tool_call_count must be an integer."
        )

    if step_count < 0:
        raise ValueError(
            "step_count cannot be negative."
        )

    if tool_call_count < 0:
        raise ValueError(
            "tool_call_count cannot be negative."
        )

    if step_count > limits.max_steps:
        raise ExecutionLimitExceededError(
            "Harbor exceeded the maximum allowed "
            f"agent steps ({limits.max_steps})."
        )

    if tool_call_count > limits.max_tool_calls:
        raise ExecutionLimitExceededError(
            "Harbor exceeded the maximum allowed "
            f"tool calls ({limits.max_tool_calls})."
        )


def increment_step_count(
    current_count: int,
    limits: ExecutionLimits = DEFAULT_EXECUTION_LIMITS,
) -> int:
    """
    Increment and validate Harbor's graph-step counter.
    """

    new_count = current_count + 1

    validate_execution_counts(
        step_count=new_count,
        tool_call_count=0,
        limits=limits,
    )

    return new_count


def increment_tool_call_count(
    current_count: int,
    limits: ExecutionLimits = DEFAULT_EXECUTION_LIMITS,
) -> int:
    """
    Increment and validate Harbor's tool-call counter.
    """

    new_count = current_count + 1

    validate_execution_counts(
        step_count=0,
        tool_call_count=new_count,
        limits=limits,
    )

    return new_count