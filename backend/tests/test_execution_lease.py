from datetime import datetime, timezone

import pytest

from app.tickets.execution_lease import (
    InvalidExecutionLeaseError,
    is_execution_lease_stale,
)


NOW = datetime(
    2026,
    9,
    15,
    12,
    0,
    0,
    tzinfo=timezone.utc,
)


def test_recent_execution_lease_is_active():
    result = is_execution_lease_stale(
        execution_started_at=(
            "2026-09-15T11:59:00+00:00"
        ),
        now=NOW,
        lease_seconds=300,
    )

    assert result is False


def test_old_execution_lease_is_stale():
    result = is_execution_lease_stale(
        execution_started_at=(
            "2026-09-15T11:54:00+00:00"
        ),
        now=NOW,
        lease_seconds=300,
    )

    assert result is True


def test_exact_boundary_is_stale():
    result = is_execution_lease_stale(
        execution_started_at=(
            "2026-09-15T11:55:00+00:00"
        ),
        now=NOW,
        lease_seconds=300,
    )

    assert result is True


def test_timezone_offset_is_normalized_to_utc():
    result = is_execution_lease_stale(
        execution_started_at=(
            "2026-09-15T16:54:00+05:00"
        ),
        now=NOW,
        lease_seconds=300,
    )

    assert result is True


def test_future_timestamp_is_rejected():
    with pytest.raises(
        InvalidExecutionLeaseError,
        match="cannot be in the future",
    ):
        is_execution_lease_stale(
            execution_started_at=(
                "2026-09-15T12:01:00+00:00"
            ),
            now=NOW,
        )


def test_empty_timestamp_is_rejected():
    with pytest.raises(
        InvalidExecutionLeaseError,
        match="cannot be empty",
    ):
        is_execution_lease_stale(
            execution_started_at="   ",
            now=NOW,
        )


def test_invalid_timestamp_is_rejected():
    with pytest.raises(
        InvalidExecutionLeaseError,
        match="valid ISO-8601",
    ):
        is_execution_lease_stale(
            execution_started_at="not-a-date",
            now=NOW,
        )


def test_naive_timestamp_is_rejected():
    with pytest.raises(
        InvalidExecutionLeaseError,
        match="timezone",
    ):
        is_execution_lease_stale(
            execution_started_at=(
                "2026-09-15T11:50:00"
            ),
            now=NOW,
        )


def test_naive_now_is_rejected():
    naive_now = datetime(
        2026,
        9,
        15,
        12,
        0,
        0,
    )

    with pytest.raises(
        InvalidExecutionLeaseError,
        match="now must include timezone",
    ):
        is_execution_lease_stale(
            execution_started_at=(
                "2026-09-15T11:50:00+00:00"
            ),
            now=naive_now,
        )


@pytest.mark.parametrize(
    "lease_seconds",
    [
        0,
        -1,
    ],
)
def test_non_positive_lease_duration_is_rejected(
    lease_seconds,
):
    with pytest.raises(
        InvalidExecutionLeaseError,
        match="greater than zero",
    ):
        is_execution_lease_stale(
            execution_started_at=(
                "2026-09-15T11:50:00+00:00"
            ),
            now=NOW,
            lease_seconds=lease_seconds,
        )


def test_non_string_timestamp_is_rejected():
    with pytest.raises(
        TypeError,
        match="must be a string",
    ):
        is_execution_lease_stale(
            execution_started_at=123,
            now=NOW,
        )


def test_non_integer_lease_duration_is_rejected():
    with pytest.raises(
        TypeError,
        match="must be an integer",
    ):
        is_execution_lease_stale(
            execution_started_at=(
                "2026-09-15T11:50:00+00:00"
            ),
            now=NOW,
            lease_seconds=300.5,
        )