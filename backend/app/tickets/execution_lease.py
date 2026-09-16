from datetime import datetime, timedelta, timezone


DEFAULT_EXECUTION_LEASE_SECONDS = 300


class InvalidExecutionLeaseError(ValueError):
    """
    Raised when Harbor cannot safely interpret execution
    lease metadata.
    """


def is_execution_lease_stale(
    *,
    execution_started_at: str,
    now: datetime | None = None,
    lease_seconds: int = DEFAULT_EXECUTION_LEASE_SECONDS,
) -> bool:
    """
    Determine whether an execution claim has exceeded its
    allowed lease duration.

    Harbor uses UTC-aware timestamps so stale-claim decisions
    do not depend on the server's local timezone.

    A lease becomes stale when its age is greater than or
    equal to the configured lease duration.
    """

    if not isinstance(execution_started_at, str):
        raise TypeError(
            "execution_started_at must be a string."
        )

    execution_started_at = (
        execution_started_at.strip()
    )

    if not execution_started_at:
        raise InvalidExecutionLeaseError(
            "execution_started_at cannot be empty."
        )

    if not isinstance(lease_seconds, int):
        raise TypeError(
            "lease_seconds must be an integer."
        )

    if lease_seconds <= 0:
        raise InvalidExecutionLeaseError(
            "lease_seconds must be greater than zero."
        )

    try:
        started_at = datetime.fromisoformat(
            execution_started_at
        )
    except ValueError as exc:
        raise InvalidExecutionLeaseError(
            "execution_started_at must be a valid "
            "ISO-8601 timestamp."
        ) from exc

    if started_at.tzinfo is None:
        raise InvalidExecutionLeaseError(
            "execution_started_at must include timezone "
            "information."
        )

    if now is None:
        now = datetime.now(
            timezone.utc
        )

    if not isinstance(now, datetime):
        raise TypeError(
            "now must be a datetime."
        )

    if now.tzinfo is None:
        raise InvalidExecutionLeaseError(
            "now must include timezone information."
        )

    started_at_utc = started_at.astimezone(
        timezone.utc
    )

    now_utc = now.astimezone(
        timezone.utc
    )

    # A future claim timestamp indicates inconsistent clock
    # or persisted data. Failing closed is safer than treating
    # it as an active or stale lease.
    if started_at_utc > now_utc:
        raise InvalidExecutionLeaseError(
            "execution_started_at cannot be in the future."
        )

    lease_duration = timedelta(
        seconds=lease_seconds
    )

    lease_age = (
        now_utc - started_at_utc
    )

    return lease_age >= lease_duration