"""Kudos schemas."""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# Page-size policy for the kudos feed. These bound how many rows a single
# request can pull back: DEFAULT is what a caller gets when they don't ask,
# MAX is the hard ceiling so nobody can request the entire table at once.
DEFAULT_FEED_LIMIT = 20
MAX_FEED_LIMIT = 100


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


class KudosFeedPage(BaseModel):
    """One page of the kudos feed plus the cursor for the next page."""

    items: list[KudosResponse]
    next_cursor: str | None = Field(
        default=None,
        description=(
            "Opaque cursor. Pass it back as ?cursor=... to fetch the next "
            "page. null means there are no more items."
        ),
    )
