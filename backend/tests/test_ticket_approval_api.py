from uuid import uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.tickets import (
    decide_ticket,
)
from app.dependencies.auth import (
    require_roles,
)
from app.main import app
from app.services.ticket_service import (
    TicketAlreadyDecidedError,
    TicketNotFoundError,
)


client = TestClient(app)


def test_ticket_approval_route_exists():
    """
    Verify that Harbor exposes the ticket approval endpoint
    through its public OpenAPI schema.

    OpenAPI is used instead of inspecting FastAPI's internal
    router representation because router internals can differ
    between FastAPI/Starlette versions.
    """

    openapi_schema = app.openapi()

    paths = openapi_schema["paths"]

    assert (
        "/api/v1/tickets/{ticket_id}/approval"
        in paths
    )

    assert (
        "post"
        in paths[
            "/api/v1/tickets/{ticket_id}/approval"
        ]
    )

def test_require_roles_allows_support_agent():
    """
    The RBAC dependency must allow a support agent.
    """

    dependency = require_roles(
        "support_agent",
        "admin",
    )

    user = {
        "id": str(uuid4()),
        "role": "support_agent",
    }

    result = dependency(
        current_user=user
    )

    assert result == user


def test_require_roles_allows_admin():
    """
    The RBAC dependency must allow an administrator.
    """

    dependency = require_roles(
        "support_agent",
        "admin",
    )

    user = {
        "id": str(uuid4()),
        "role": "admin",
    }

    result = dependency(
        current_user=user
    )

    assert result == user


def test_require_roles_blocks_customer():
    """
    A normal customer must never be able to approve or
    reject another support ticket.
    """

    dependency = require_roles(
        "support_agent",
        "admin",
    )

    user = {
        "id": str(uuid4()),
        "role": "customer",
    }

    try:
        dependency(
            current_user=user
        )
        assert False, (
            "Customer should not have approval permission."
        )

    except HTTPException as exc:
        assert exc.status_code == 403


def test_approve_ticket_endpoint(
    monkeypatch,
):
    """
    Verify that an authorized reviewer can approve a ticket
    and that the authenticated reviewer's ID is passed into
    the service layer.
    """

    ticket_id = uuid4()
    reviewer_id = uuid4()

    captured = {}

    def fake_decide_ticket_approval(
        *,
        ticket_id,
        reviewer_id,
        approved,
    ):
        captured["ticket_id"] = ticket_id
        captured["reviewer_id"] = reviewer_id
        captured["approved"] = approved

        return {
            "ticket_id": ticket_id,
            "approval_status": "approved",
            "status": "approved",
            "approved_by": reviewer_id,
            "approved_at": None,
        }

    monkeypatch.setattr(
        "app.api.tickets.decide_ticket_approval",
        fake_decide_ticket_approval,
    )

    result = decide_ticket(
        ticket_id=ticket_id,
        payload=type(
            "ApprovalRequest",
            (),
            {"approved": True},
        )(),
        current_user={
            "id": str(reviewer_id),
            "role": "support_agent",
        },
    )

    assert (
        captured["ticket_id"]
        == str(ticket_id)
    )

    assert (
        captured["reviewer_id"]
        == str(reviewer_id)
    )

    assert captured["approved"] is True

    assert (
        result["approval_status"]
        == "approved"
    )


def test_reject_ticket_endpoint(
    monkeypatch,
):
    """
    Verify that an authorized reviewer can reject a ticket.
    """

    ticket_id = uuid4()
    reviewer_id = uuid4()

    captured = {}

    def fake_decide_ticket_approval(
        *,
        ticket_id,
        reviewer_id,
        approved,
    ):
        captured["approved"] = approved

        return {
            "ticket_id": ticket_id,
            "approval_status": "rejected",
            "status": "rejected",
            "approved_by": reviewer_id,
            "approved_at": None,
        }

    monkeypatch.setattr(
        "app.api.tickets.decide_ticket_approval",
        fake_decide_ticket_approval,
    )

    result = decide_ticket(
        ticket_id=ticket_id,
        payload=type(
            "ApprovalRequest",
            (),
            {"approved": False},
        )(),
        current_user={
            "id": str(reviewer_id),
            "role": "admin",
        },
    )

    assert captured["approved"] is False

    assert (
        result["approval_status"]
        == "rejected"
    )


def test_missing_ticket_returns_404(
    monkeypatch,
):
    """
    Convert the service's not-found error into HTTP 404.
    """

    def fake_decide_ticket_approval(
        **kwargs,
    ):
        raise TicketNotFoundError(
            "Support ticket was not found."
        )

    monkeypatch.setattr(
        "app.api.tickets.decide_ticket_approval",
        fake_decide_ticket_approval,
    )

    try:
        decide_ticket(
            ticket_id=uuid4(),
            payload=type(
                "ApprovalRequest",
                (),
                {"approved": True},
            )(),
            current_user={
                "id": str(uuid4()),
                "role": "support_agent",
            },
        )

        assert False, (
            "Missing ticket should return HTTP 404."
        )

    except HTTPException as exc:
        assert exc.status_code == 404
        assert (
            exc.detail
            == "Support ticket was not found."
        )


def test_already_decided_ticket_returns_409(
    monkeypatch,
):
    """
    Convert an invalid workflow transition into HTTP 409.
    """

    def fake_decide_ticket_approval(
        **kwargs,
    ):
        raise TicketAlreadyDecidedError(
            "Support ticket has already been decided."
        )

    monkeypatch.setattr(
        "app.api.tickets.decide_ticket_approval",
        fake_decide_ticket_approval,
    )

    try:
        decide_ticket(
            ticket_id=uuid4(),
            payload=type(
                "ApprovalRequest",
                (),
                {"approved": True},
            )(),
            current_user={
                "id": str(uuid4()),
                "role": "admin",
            },
        )

        assert False, (
            "Already-decided ticket should return HTTP 409."
        )

    except HTTPException as exc:
        assert exc.status_code == 409
        assert (
            exc.detail
            == "Support ticket has already been decided."
        )