"""Business logic for pulse check-in operations."""

import uuid
from datetime import date

from sqlalchemy import case, func, select
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
        stmt = (
            select(PulseEntry)
            .where(PulseEntry.user_id == user_id)
            .order_by(PulseEntry.pulse_date.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_team_summary(self, target_date: date | None = None) -> PulseTeamResponse:
        """Get aggregated team pulse data for a given date."""
        if target_date is None:
            target_date = date.today()

        # Step 1: get the raw rows for the date (needed for `entries`)
        entries_stmt = select(PulseEntry).where(PulseEntry.pulse_date == target_date)
        entries_result = await self.db.execute(entries_stmt)
        entries = list(entries_result.scalars().all())

        # Step 2: get the aggregates from the SAME filtered set
        agg_stmt = select(
            func.avg(PulseEntry.mood).label("avg_mood"),
            func.avg(PulseEntry.energy).label("avg_energy"),
            func.count(PulseEntry.id).label("total_responses"),
            func.count(case((PulseEntry.has_blocker.is_(True), 1))).label("blocker_count"),
        ).where(PulseEntry.pulse_date == target_date)

        agg_result = await self.db.execute(agg_stmt)
        row = agg_result.one()

        return PulseTeamResponse(
            date=target_date,
            avg_mood=round(row.avg_mood, 2) if row.avg_mood is not None else 0.0,
            avg_energy=round(row.avg_energy, 2) if row.avg_energy is not None else 0.0,
            blocker_count=row.blocker_count or 0,
            total_responses=row.total_responses or 0,
            entries=entries,
        )
