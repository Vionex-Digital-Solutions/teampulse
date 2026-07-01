"""Standup schemas."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class StandupCreate(BaseModel):
    """Schema for submitting a standup entry."""

    yesterday: str = Field(..., min_length=1, max_length=2000)
    today: str = Field(..., min_length=1, max_length=2000)
    blockers: str | None = Field(default=None, max_length=2000)
    tags: list[str] | None = Field(default=None)


class StandupResponse(BaseModel):
    """Schema for a standup entry response."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    standup_date: date
    yesterday: str
    today: str
    blockers: str | None
    tags: str | None
    created_at: datetime
