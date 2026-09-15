from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.repositories.ticket_repository import (
    create_ticket,
    get_ticket,
    get_ticket_by_idempotency_key,
    list_tickets,
)
from app.tickets.schemas import TicketCreate


def make_ticket() -> TicketCreate:
    """
    Build a valid internal ticket for repository tests.
    """

    return TicketCreate(
        user_id=uuid4(),
        conversation_id=uuid4(),
        title="Refund requires human review",
        description=(
            "The customer's refund remains pending "
            "beyond the expected processing period."
        ),
        severity="high",
        idempotency_key="ticket-test-key-123",
    )


@patch(
    "app.repositories.ticket_repository."
    "get_supabase_client"
)
def test_get_ticket_by_idempotency_key(
    mock_get_client,
):
    client = MagicMock()
    mock_get_client.return_value = client

    existing = {
        "id": str(uuid4()),
        "user_id": str(uuid4()),
        "idempotency_key": "ticket-test-key-123",
    }

    client.table.return_value.select.return_value \
        .eq.return_value.eq.return_value \
        .limit.return_value.execute.return_value = (
            SimpleNamespace(
                data=[existing]
            )
        )

    result = get_ticket_by_idempotency_key(
        idempotency_key="ticket-test-key-123",
        user_id=existing["user_id"],
    )

    assert result == existing

    client.table.assert_called_once_with(
        "support_tickets"
    )


@patch(
    "app.repositories.ticket_repository."
    "get_supabase_client"
)
def test_get_ticket_by_idempotency_key_returns_none(
    mock_get_client,
):
    client = MagicMock()
    mock_get_client.return_value = client

    client.table.return_value.select.return_value \
        .eq.return_value.eq.return_value \
        .limit.return_value.execute.return_value = (
            SimpleNamespace(
                data=[]
            )
        )

    result = get_ticket_by_idempotency_key(
        idempotency_key="missing-key",
        user_id=str(uuid4()),
    )

    assert result is None


def test_get_ticket_by_idempotency_key_rejects_empty_key():
    with pytest.raises(
        ValueError,
        match="Idempotency key cannot be empty",
    ):
        get_ticket_by_idempotency_key(
            idempotency_key="   ",
            user_id=str(uuid4()),
        )


@patch(
    "app.repositories.ticket_repository."
    "get_supabase_client"
)
@patch(
    "app.repositories.ticket_repository."
    "get_ticket_by_idempotency_key"
)
def test_create_ticket_inserts_new_ticket(
    mock_get_existing,
    mock_get_client,
):
    mock_get_existing.return_value = None

    client = MagicMock()
    mock_get_client.return_value = client

    ticket = make_ticket()

    inserted = {
        "id": str(uuid4()),
        "user_id": str(ticket.user_id),
        "conversation_id": str(
            ticket.conversation_id
        ),
        "title": ticket.title,
        "description": ticket.description,
        "severity": "high",
        "status": "pending_approval",
        "approval_status": "pending",
        "idempotency_key": (
            ticket.idempotency_key
        ),
    }

    client.table.return_value.insert.return_value \
        .execute.return_value = (
            SimpleNamespace(
                data=[inserted]
            )
        )

    result = create_ticket(ticket)

    assert result == inserted

    client.table.assert_called_once_with(
        "support_tickets"
    )

    payload = (
        client.table.return_value
        .insert.call_args.args[0]
    )

    assert payload["status"] == (
        "pending_approval"
    )
    assert payload["approval_status"] == "pending"
    assert payload["user_id"] == str(
        ticket.user_id
    )


@patch(
    "app.repositories.ticket_repository."
    "get_supabase_client"
)
@patch(
    "app.repositories.ticket_repository."
    "get_ticket_by_idempotency_key"
)
def test_create_ticket_returns_existing_ticket(
    mock_get_existing,
    mock_get_client,
):
    ticket = make_ticket()

    existing = {
        "id": str(uuid4()),
        "user_id": str(ticket.user_id),
        "idempotency_key": (
            ticket.idempotency_key
        ),
        "status": "pending_approval",
    }

    mock_get_existing.return_value = existing

    result = create_ticket(ticket)

    assert result == existing

    # The database insert path must never run when the
    # idempotency key already represents a ticket.
    mock_get_client.assert_not_called()


@patch(
    "app.repositories.ticket_repository."
    "get_supabase_client"
)
@patch(
    "app.repositories.ticket_repository."
    "get_ticket_by_idempotency_key"
)
def test_create_ticket_raises_when_insert_returns_no_data(
    mock_get_existing,
    mock_get_client,
):
    mock_get_existing.return_value = None

    client = MagicMock()
    mock_get_client.return_value = client

    client.table.return_value.insert.return_value \
        .execute.return_value = (
            SimpleNamespace(
                data=[]
            )
        )

    with pytest.raises(
        RuntimeError,
        match="Failed to create support ticket",
    ):
        create_ticket(
            make_ticket()
        )


@patch(
    "app.repositories.ticket_repository."
    "get_supabase_client"
)
def test_get_ticket_enforces_user_ownership(
    mock_get_client,
):
    client = MagicMock()
    mock_get_client.return_value = client

    ticket_id = str(uuid4())
    user_id = str(uuid4())

    stored = {
        "id": ticket_id,
        "user_id": user_id,
    }

    first_eq = MagicMock()
    second_eq = MagicMock()
    limit_query = MagicMock()

    client.table.return_value.select.return_value \
        .eq.return_value = first_eq

    first_eq.eq.return_value = second_eq
    second_eq.limit.return_value = limit_query

    limit_query.execute.return_value = (
        SimpleNamespace(
            data=[stored]
        )
    )

    result = get_ticket(
        ticket_id=ticket_id,
        user_id=user_id,
    )

    assert result == stored

    client.table.return_value.select.return_value \
        .eq.assert_called_once_with(
            "id",
            ticket_id,
        )

    first_eq.eq.assert_called_once_with(
        "user_id",
        user_id,
    )


@patch(
    "app.repositories.ticket_repository."
    "get_supabase_client"
)
def test_get_ticket_returns_none_when_unavailable(
    mock_get_client,
):
    client = MagicMock()
    mock_get_client.return_value = client

    client.table.return_value.select.return_value \
        .eq.return_value.eq.return_value \
        .limit.return_value.execute.return_value = (
            SimpleNamespace(
                data=[]
            )
        )

    result = get_ticket(
        ticket_id=str(uuid4()),
        user_id=str(uuid4()),
    )

    assert result is None


@patch(
    "app.repositories.ticket_repository."
    "get_supabase_client"
)
def test_list_tickets_returns_rows(
    mock_get_client,
):
    client = MagicMock()
    mock_get_client.return_value = client

    rows = [
        {"id": str(uuid4())},
        {"id": str(uuid4())},
    ]

    client.table.return_value.select.return_value \
        .eq.return_value.order.return_value \
        .limit.return_value.execute.return_value = (
            SimpleNamespace(
                data=rows
            )
        )

    result = list_tickets(
        user_id=str(uuid4()),
        limit=20,
    )

    assert result == rows

    client.table.assert_called_once_with(
        "support_tickets"
    )


@patch(
    "app.repositories.ticket_repository."
    "get_supabase_client"
)
def test_list_tickets_returns_empty_list(
    mock_get_client,
):
    client = MagicMock()
    mock_get_client.return_value = client

    client.table.return_value.select.return_value \
        .eq.return_value.order.return_value \
        .limit.return_value.execute.return_value = (
            SimpleNamespace(
                data=None
            )
        )

    result = list_tickets(
        user_id=str(uuid4())
    )

    assert result == []


def test_list_tickets_rejects_invalid_limit():
    with pytest.raises(
        ValueError,
        match=(
            "Ticket list limit must be "
            "greater than zero"
        ),
    ):
        list_tickets(
            user_id=str(uuid4()),
            limit=0,
        )