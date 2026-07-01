"""Weekly digest generation service."""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession


class DigestService:
    """Service for generating weekly team health digests."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate_weekly_digest(self, week_ending: date | None = None) -> dict:
        """Generate a comprehensive weekly team health digest."""
        raise NotImplementedError("Sprint 3: implement weekly digest generation")

    async def get_mood_trend(self, days: int = 7) -> list[dict]:
        """Get daily mood averages for the last N days."""
        raise NotImplementedError("Sprint 3: implement mood trend calculation")

    async def get_standup_completion_rate(self, days: int = 7) -> float:
        """Get the percentage of team members who submitted standups."""
        raise NotImplementedError("Sprint 3: implement standup completion rate")
