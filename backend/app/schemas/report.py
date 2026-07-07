"""Reporting schemas (read-only analytics responses)."""

import uuid

from pydantic import BaseModel


class TopBlockerRow(BaseModel):
    """One row of the 'most blockers this week' report: a user and their count."""

    model_config = {"from_attributes": True}

    user_id: uuid.UUID
    display_name: str
    blocker_count: int
