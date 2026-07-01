"""Kudos schemas."""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class KudosCategory(str, Enum):
    """Allowed kudos categories."""

    TEAMWORK = "teamwork"
    INNOVATION = "innovation"
    MENTORSHIP = "mentorship"
    ABOVE_AND_BEYOND = "above_and_beyond"
    QUALITY = "quality"
    COMMUNICATION = "communication"


class KudosCreate(BaseModel):
    """Schema for sending kudos."""

    receiver_id: uuid.UUID
    category: KudosCategory
    message: str = Field(..., min_length=1, max_length=1000)
    message_ar: str | None = Field(default=None, max_length=1000)


class KudosResponse(BaseModel):
    """Schema for a kudos entry response."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    sender_id: uuid.UUID
    receiver_id: uuid.UUID
    category: str
    message: str
    message_ar: str | None
    created_at: datetime
