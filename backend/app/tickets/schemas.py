from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    StrictBool,
)


# ============================================================
# TICKET TYPES
# ============================================================

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


TicketUpdateType = Literal[
    "customer_reply",
    "staff_reply",
    "internal_note",
]


# ============================================================
# CUSTOMER PROFILE
# ============================================================

class TicketCustomer(BaseModel):
    """
    Support-relevant customer profile information.

    This object is attached only when Harbor enriches a
    ticket for staff-facing responses.
    """

    id: UUID
    email: str

    full_name: str | None = None
    age: int | None = None
    country: str | None = None


# ============================================================
# TICKET CREATION
# ============================================================

class TicketCreate(BaseModel):
    """
    Internal request used when Harbor creates a support
    ticket after customer confirmation.

    Creating this record does not execute an external
    business action.
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


# ============================================================
# COMPLETE TICKET RECORD
# ============================================================

class TicketRecord(TicketCreate):
    """
    Complete persisted Harbor support ticket.
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

    execution_claim_id: UUID | None = None

    execution_started_at: (
        datetime | None
    ) = None

    monday_item_id: str | None = None

    external_status: str | None = None

    last_synced_at: datetime | None = None

    failure_reason: str | None = None

    created_at: datetime
    updated_at: datetime

    customer: TicketCustomer | None = None


# ============================================================
# HUMAN APPROVAL
# ============================================================

class TicketApprovalRequest(BaseModel):
    """
    Human approval or rejection request.
    """

    approved: StrictBool


class TicketApprovalResult(BaseModel):
    """
    Result returned after Harbor records the human
    decision.
    """

    ticket_id: UUID

    approval_status: ApprovalStatus
    status: TicketStatus

    approved_by: UUID | None = None
    approved_at: datetime | None = None


# ============================================================
# CUSTOMER TICKET REPLIES
# ============================================================

class TicketUpdateRequest(BaseModel):
    """
    Customer reply payload.

    Customers cannot choose their update type.
    Harbor always persists this request as customer_reply.
    """

    content: str = Field(
        min_length=1,
        max_length=5000,
    )


# ============================================================
# STAFF REPLY / INTERNAL NOTE
# ============================================================

class StaffTicketUpdateRequest(BaseModel):
    """
    Authorized staff can either:

    - reply to the customer;
    - create a staff-only internal note.
    """

    content: str = Field(
        min_length=1,
        max_length=5000,
    )

    update_type: Literal[
        "staff_reply",
        "internal_note",
    ]


# ============================================================
# TICKET UPDATE AUTHOR
# ============================================================

class TicketUpdateAuthor(BaseModel):
    """
    Safe author information returned with ticket updates.
    """

    id: UUID

    full_name: str | None = None
    email: str | None = None

    role: str


# ============================================================
# COMPLETE UPDATE RECORD
# ============================================================

class TicketUpdateRecord(BaseModel):
    """
    One entry in a support ticket conversation timeline.
    """

    id: UUID
    ticket_id: UUID
    author_id: UUID

    author_role: str

    update_type: TicketUpdateType

    content: str

    created_at: datetime

    author: TicketUpdateAuthor | None = None