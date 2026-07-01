"""Pulse check-in schemas."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class PulseCreate(BaseModel):
    """Schema for submitting a pulse check-in."""

    mood: int = Field(..., ge=1, le=5, description="Mood score 1-5")
    energy: int = Field(..., ge=1, le=5, description="Energy level 1-5")
    has_blocker: bool = Field(default=False, description="Whether the user has a blocker")
    note: str | None = Field(default=None, max_length=500)
    note_ar: str | None = Field(default=None, max_length=500)


class PulseResponse(BaseModel):
    """Schema for a single pulse entry response."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    pulse_date: date
    mood: int
    energy: int
    has_blocker: bool
    note: str | None
    note_ar: str | None
    created_at: datetime


class PulseTeamResponse(BaseModel):
    """Aggregated team pulse response."""

    date: date
    avg_mood: float
    avg_energy: float
    blocker_count: int
    total_responses: int
    entries: list[PulseResponse]
