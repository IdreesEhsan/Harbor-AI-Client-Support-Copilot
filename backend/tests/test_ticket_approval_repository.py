from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.repositories.ticket_repository import (
    approve_ticket,
    get_ticket_for_review,
    reject_ticket,
)


@patch(
    "app.repositories.ticket_repository."
    "get_supabase_client"
)
def test_get_ticket_for_review_returns_ticket(
    mock_get_client,
):
    client = MagicMock()
    mock_get_client.return_value = client

    ticket_id = str(uuid4())

    ticket = {
        "id": ticket_id,
        "status": "pending_approval",
        "approval_status": "pending",
    }

    client.table.return_value.select.return_value \
        .eq.return_value.limit.return_value \
        .execute.return_value = (
            SimpleNamespace(
                data=[ticket]
            )
        )

    result = get_ticket_for_review(
        ticket_id
    )

    assert result == ticket

    client.table.assert_called_once_with(
        "support_tickets"
    )

    client.table.return_value.select.return_value \
        .eq.assert_called_once_with(
            "id",
            ticket_id,
        )


@patch(
    "app.repositories.ticket_repository."
    "get_supabase_client"
)
def test_get_ticket_for_review_returns_none(
    mock_get_client,
):
    client = MagicMock()
    mock_get_client.return_value = client

    client.table.return_value.select.return_value \
        .eq.return_value.limit.return_value \
        .execute.return_value = (
            SimpleNamespace(
                data=[]
            )
        )

    result = get_ticket_for_review(
        str(uuid4())
    )

    assert result is None


@patch(
    "app.repositories.ticket_repository."
    "get_supabase_client"
)
def test_approve_ticket_updates_pending_ticket(
    mock_get_client,
):
    client = MagicMock()
    mock_get_client.return_value = client

    ticket_id = str(uuid4())
    reviewer_id = str(uuid4())

    approved = {
        "id": ticket_id,
        "status": "approved",
        "approval_status": "approved",
        "approved_by": reviewer_id,
    }

    first_eq = MagicMock()
    second_eq = MagicMock()
    third_eq = MagicMock()

    client.table.return_value.update.return_value \
        .eq.return_value = first_eq

    first_eq.eq.return_value = second_eq
    second_eq.eq.return_value = third_eq

    third_eq.execute.return_value = (
        SimpleNamespace(
            data=[approved]
        )
    )

    result = approve_ticket(
        ticket_id=ticket_id,
        approved_by=reviewer_id,
    )

    assert result == approved

    payload = (
        client.table.return_value
        .update.call_args.args[0]
    )

    assert (
        payload["approval_status"]
        == "approved"
    )
    assert payload["status"] == "approved"
    assert payload["approved_by"] == reviewer_id
    assert payload["approved_at"]
    assert payload["updated_at"]

    client.table.return_value.update.return_value \
        .eq.assert_called_once_with(
            "id",
            ticket_id,
        )

    first_eq.eq.assert_called_once_with(
        "approval_status",
        "pending",
    )

    second_eq.eq.assert_called_once_with(
        "status",
        "pending_approval",
    )


@patch(
    "app.repositories.ticket_repository."
    "get_supabase_client"
)
def test_approve_ticket_returns_none_when_not_pending(
    mock_get_client,
):
    client = MagicMock()
    mock_get_client.return_value = client

    client.table.return_value.update.return_value \
        .eq.return_value.eq.return_value \
        .eq.return_value.execute.return_value = (
            SimpleNamespace(
                data=[]
            )
        )

    result = approve_ticket(
        ticket_id=str(uuid4()),
        approved_by=str(uuid4()),
    )

    assert result is None


@patch(
    "app.repositories.ticket_repository."
    "get_supabase_client"
)
def test_reject_ticket_updates_pending_ticket(
    mock_get_client,
):
    client = MagicMock()
    mock_get_client.return_value = client

    ticket_id = str(uuid4())
    reviewer_id = str(uuid4())

    rejected = {
        "id": ticket_id,
        "status": "rejected",
        "approval_status": "rejected",
        "approved_by": reviewer_id,
    }

    first_eq = MagicMock()
    second_eq = MagicMock()
    third_eq = MagicMock()

    client.table.return_value.update.return_value \
        .eq.return_value = first_eq

    first_eq.eq.return_value = second_eq
    second_eq.eq.return_value = third_eq

    third_eq.execute.return_value = (
        SimpleNamespace(
            data=[rejected]
        )
    )

    result = reject_ticket(
        ticket_id=ticket_id,
        rejected_by=reviewer_id,
    )

    assert result == rejected

    payload = (
        client.table.return_value
        .update.call_args.args[0]
    )

    assert (
        payload["approval_status"]
        == "rejected"
    )
    assert payload["status"] == "rejected"
    assert payload["approved_by"] == reviewer_id
    assert payload["approved_at"]
    assert payload["updated_at"]

    client.table.return_value.update.return_value \
        .eq.assert_called_once_with(
            "id",
            ticket_id,
        )

    first_eq.eq.assert_called_once_with(
        "approval_status",
        "pending",
    )

    second_eq.eq.assert_called_once_with(
        "status",
        "pending_approval",
    )


@patch(
    "app.repositories.ticket_repository."
    "get_supabase_client"
)
def test_reject_ticket_returns_none_when_not_pending(
    mock_get_client,
):
    client = MagicMock()
    mock_get_client.return_value = client

    client.table.return_value.update.return_value \
        .eq.return_value.eq.return_value \
        .eq.return_value.execute.return_value = (
            SimpleNamespace(
                data=[]
            )
        )

    result = reject_ticket(
        ticket_id=str(uuid4()),
        rejected_by=str(uuid4()),
    )

    assert result is None