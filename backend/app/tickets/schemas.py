from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    StrictBool,
)


TicketSeverity = Literal[
    "low",
    "medium",
    "high",
    "critical",
]

TicketStatus = Literal[
    "pending_approval",
    "approved",
    "rejected",
    "executing",
    "open",
    "in_progress",
    "resolved",
    "closed",
    "failed",
]

ApprovalStatus = Literal[
    "pending",
    "approved",
    "rejected",
]


class TicketCustomer(BaseModel):
    """
    Customer profile information exposed to authorized
    support staff together with a support ticket.
    """

    id: UUID
    email: str

    full_name: str | None = None
    age: int | None = None
    country: str | None = None


class TicketCreate(BaseModel):
    """
    Internal request used when Harbor creates a support
    ticket after customer confirmation.
    """

    user_id: UUID
    conversation_id: UUID

    title: str = Field(
        min_length=1,
        max_length=200,
    )

    description: str = Field(
        min_length=1,
        max_length=5000,
    )

    severity: TicketSeverity = "medium"

    idempotency_key: str = Field(
        min_length=1,
        max_length=255,
    )


class TicketRecord(TicketCreate):
    """
    Complete persisted Harbor ticket.

    customer is populated only when the backend enriches
    the response for authorized support staff.

    It remains optional so existing customer and execution
    workflows continue to work without requiring customer
    enrichment.
    """

    id: UUID

    status: TicketStatus = (
        "pending_approval"
    )

    approval_status: ApprovalStatus = (
        "pending"
    )

    approved_by: UUID | None = None
    approved_at: datetime | None = None

    execution_claim_id: (
        UUID | None
    ) = None

    execution_started_at: (
        datetime | None
    ) = None

    monday_item_id: str | None = None

    external_status: str | None = None

    last_synced_at: (
        datetime | None
    ) = None

    failure_reason: str | None = None

    created_at: datetime
    updated_at: datetime

    customer: TicketCustomer | None = None


class TicketApprovalRequest(BaseModel):
    """
    Human decision for a pending support ticket.
    """

    approved: StrictBool


class TicketApprovalResult(BaseModel):
    """
    Result returned after Harbor records a human
    approval decision.
    """

    ticket_id: UUID

    approval_status: ApprovalStatus
    status: TicketStatus

    approved_by: UUID | None = None
    approved_at: datetime | None = None