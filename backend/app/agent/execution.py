from collections.abc import Callable
from typing import Any

from app.agent.state import HarborAgentState
from app.guardrails.execution_control import (
    increment_step_count,
)


AgentNode = Callable[
    [HarborAgentState],
    dict[str, Any],
]


def controlled_node(
    node: AgentNode,
) -> AgentNode:
    """
    Wrap a LangGraph node with request-scoped step counting.

    Every time LangGraph executes the wrapped node, Harbor
    increments the step counter before allowing the node's
    business logic to run.

    If the configured execution limit has already been
    consumed, increment_step_count raises
    ExecutionLimitExceededError and the protected node is
    never executed.

    Keeping this behavior centralized prevents execution
    safety logic from being duplicated across every node.
    """

    def wrapped(
        state: HarborAgentState,
    ) -> dict[str, Any]:

        current_step_count = state.get(
            "step_count",
            0,
        )

        # Increment BEFORE node execution.
        #
        # This means a node that would exceed Harbor's
        # configured execution limit never runs.
        new_step_count = increment_step_count(
            current_step_count
        )

        result = node(state)

        # Never mutate the dictionary returned by the
        # underlying node. Some nodes/tests may reuse it.
        update = dict(result)

        # Persist the new request-scoped count into
        # LangGraph state.
        update["step_count"] = new_step_count

        return update

    # Preserve a useful function name for debugging and
    # LangGraph traces.
    wrapped.__name__ = (
        f"controlled_{node.__name__}"
    )

    wrapped.__doc__ = node.__doc__

    return wrapped