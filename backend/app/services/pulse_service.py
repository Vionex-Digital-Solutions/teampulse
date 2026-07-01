"""Business logic for pulse check-in operations."""

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pulse import PulseEntry
from app.schemas.pulse import PulseCreate, PulseTeamResponse


class PulseService:
    """Service for managing pulse check-in entries."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_pulse(self, user_id: uuid.UUID, payload: PulseCreate) -> PulseEntry:
        """Create a new pulse entry for a user. One per user per day."""
        raise NotImplementedError("Sprint 1: implement pulse creation logic")

    async def get_user_pulses(
        self, user_id: uuid.UUID, limit: int = 30
    ) -> list[PulseEntry]:
        """Get a user's pulse history, most recent first."""
        raise NotImplementedError("Sprint 1: implement user pulse retrieval")

    async def get_team_summary(self, target_date: date | None = None) -> PulseTeamResponse:
        """Get aggregated team pulse data for a given date."""
        raise NotImplementedError("Sprint 1: implement team pulse aggregation")
