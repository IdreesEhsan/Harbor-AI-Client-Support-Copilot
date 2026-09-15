from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    """
    Request data used when starting a new Harbor conversation.
    """

    title: str | None = Field(
        default=None,
        max_length=200,
    )


class ConversationResponse(BaseModel):
    """
    Public representation of a Harbor conversation.
    """

    id: str
    user_id: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    """
    Internal schema for storing conversation messages.
    """

    conversation_id: str

    role: Literal[
        "user",
        "assistant",
        "system",
    ]

    content: str = Field(
        min_length=1,
        max_length=20000,
    )


class MessageResponse(BaseModel):
    id: str
    conversation_id: str

    role: Literal[
        "user",
        "assistant",
        "system",
    ]

    content: str
    created_at: datetime


class ConversationSummaryResponse(BaseModel):
    id: str
    conversation_id: str
    summary: str
    summarized_until: datetime | None = None
    updated_at: datetime