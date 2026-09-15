from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, StrictBool


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


class TicketCreate(BaseModel):
    """
    Internal request for creating a Harbor support ticket.

    Creating this record does not mean an external ticket
    has been created. New tickets begin in the
    pending-approval state.
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
    Complete persisted Harbor ticket representation.
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

    monday_item_id: str | None = None
    external_status: str | None = None

    last_synced_at: datetime | None = None
    failure_reason: str | None = None

    created_at: datetime
    updated_at: datetime


class TicketApprovalRequest(BaseModel):
    """
    Human decision for a pending side-effecting ticket.
    """

    approved: StrictBool


class TicketApprovalResult(BaseModel):
    """
    Result returned after Harbor records an approval
    decision.
    """

    ticket_id: UUID
    approval_status: ApprovalStatus
    status: TicketStatus

    approved_by: UUID | None = None
    approved_at: datetime | None = None