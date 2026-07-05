"""Business logic for pulse check-in operations."""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pulse import PulseEntry
from app.schemas.pulse import PulseCreate, PulseTeamResponse


class PulseAlreadyExistsError(Exception):
    """Raised when a user tries to submit a second pulse on the same day."""


class PulseService:
    """Service for managing pulse check-in entries."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_pulse(self, user_id: uuid.UUID, payload: PulseCreate) -> PulseEntry:
        """Create a new pulse entry for a user. One per user per day."""
        today = datetime.now(timezone.utc).date()

        # Enforce "one check-in per user per day". We look for an existing row
        # for this user + date before inserting, since the model has no DB-level
        # unique constraint yet.
        existing = await self.db.execute(
            select(PulseEntry).where(
                PulseEntry.user_id == user_id,
                PulseEntry.pulse_date == today,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise PulseAlreadyExistsError(
                "You have already submitted a pulse check-in today."
            )

        # Build the ORM object from the validated request payload.
        entry = PulseEntry(
            user_id=user_id,
            pulse_date=today,
            mood=payload.mood,
            energy=payload.energy,
            has_blocker=payload.has_blocker,
            note=payload.note,
            note_ar=payload.note_ar,
        )

        # Stage the insert and flush so the DB assigns/populates the row.
        # flush() sends the INSERT (filling in id + created_at from the mixin
        # defaults); refresh() reloads the persisted state. The final commit is
        # handled once per request by the get_async_session dependency.
        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)
        return entry

    async def get_user_pulses(
        self, user_id: uuid.UUID, limit: int = 30
    ) -> list[PulseEntry]:
        """Get a user's pulse history, most recent first."""
        raise NotImplementedError("Sprint 1: implement user pulse retrieval")

    async def get_team_summary(self, target_date: date | None = None) -> PulseTeamResponse:
        """Get aggregated team pulse data for a given date."""
        raise NotImplementedError("Sprint 1: implement team pulse aggregation")
