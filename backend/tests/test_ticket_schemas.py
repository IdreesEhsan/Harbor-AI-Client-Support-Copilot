from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.tickets.schemas import (
    TicketApprovalRequest,
    TicketApprovalResult,
    TicketCreate,
    TicketRecord,
)


def valid_ticket_data():
    """
    Return valid ticket input shared by schema tests.
    """

    return {
        "user_id": uuid4(),
        "conversation_id": uuid4(),
        "title": "Refund requires human review",
        "description": (
            "The customer reports that their refund "
            "has remained pending beyond the expected "
            "processing period."
        ),
        "severity": "high",
        "idempotency_key": (
            "escalation-conversation-123-turn-5"
        ),
    }


def test_ticket_create_accepts_valid_data():
    ticket = TicketCreate(
        **valid_ticket_data()
    )

    assert ticket.severity == "high"

    assert (
        ticket.title
        == "Refund requires human review"
    )


def test_ticket_create_defaults_to_medium_severity():
    data = valid_ticket_data()
    data.pop("severity")

    ticket = TicketCreate(**data)

    assert ticket.severity == "medium"


def test_ticket_rejects_invalid_severity():
    data = valid_ticket_data()
    data["severity"] = "emergency"

    with pytest.raises(ValidationError):
        TicketCreate(**data)


def test_ticket_rejects_empty_title():
    data = valid_ticket_data()
    data["title"] = ""

    with pytest.raises(ValidationError):
        TicketCreate(**data)


def test_ticket_rejects_empty_description():
    data = valid_ticket_data()
    data["description"] = ""

    with pytest.raises(ValidationError):
        TicketCreate(**data)


def test_ticket_requires_idempotency_key():
    data = valid_ticket_data()
    data.pop("idempotency_key")

    with pytest.raises(ValidationError):
        TicketCreate(**data)


def test_ticket_rejects_empty_idempotency_key():
    data = valid_ticket_data()
    data["idempotency_key"] = ""

    with pytest.raises(ValidationError):
        TicketCreate(**data)


def test_ticket_record_defaults_to_pending_approval():
    data = valid_ticket_data()

    now = datetime.now(UTC)

    ticket = TicketRecord(
        **data,
        id=uuid4(),
        created_at=now,
        updated_at=now,
    )

    assert (
        ticket.status
        == "pending_approval"
    )

    assert (
        ticket.approval_status
        == "pending"
    )

    assert ticket.approved_by is None
    assert ticket.approved_at is None
    assert ticket.monday_item_id is None


def test_ticket_record_rejects_invalid_status():
    data = valid_ticket_data()

    with pytest.raises(ValidationError):
        TicketRecord(
            **data,
            id=uuid4(),
            status="whatever",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )


def test_ticket_approval_request_accepts_boolean():
    request = TicketApprovalRequest(
        approved=True
    )

    assert request.approved is True


def test_ticket_approval_request_requires_boolean():
    with pytest.raises(ValidationError):
        TicketApprovalRequest(
            approved="yes"
        )


def test_ticket_approval_result_supports_approval():
    ticket_id = uuid4()
    approver_id = uuid4()
    now = datetime.now(UTC)

    result = TicketApprovalResult(
        ticket_id=ticket_id,
        approval_status="approved",
        status="approved",
        approved_by=approver_id,
        approved_at=now,
    )

    assert result.ticket_id == ticket_id
    assert (
        result.approval_status
        == "approved"
    )
    assert result.status == "approved"
    assert result.approved_by == approver_id


def test_ticket_approval_result_rejects_invalid_state():
    with pytest.raises(ValidationError):
        TicketApprovalResult(
            ticket_id=uuid4(),
            approval_status="waiting",
            status="pending_approval",
        )