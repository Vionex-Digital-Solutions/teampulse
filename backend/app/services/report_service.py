"""Business logic for reporting/analytics read queries."""

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pulse import PulseEntry
from app.models.user import User
from app.schemas.report import TopBlockerRow


class ReportService:
    """Service for read-only reporting queries built from JOINs + CTEs."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_top_blockers(
        self, days: int = 7, limit: int = 10
    ) -> list[TopBlockerRow]:
        """Report: teammates who logged the most blockers in the last ``days`` days.

        Equivalent SQL (read top-to-bottom):

            WITH weekly_blockers AS (
                SELECT user_id, COUNT(*) AS blocker_count
                FROM pulse_entries
                WHERE has_blocker IS true
                  AND pulse_date >= :week_start
                GROUP BY user_id
            )
            SELECT wb.user_id, u.display_name, wb.blocker_count
            FROM weekly_blockers wb
            JOIN users u ON u.id = wb.user_id
            ORDER BY wb.blocker_count DESC
            LIMIT :limit;

        JOIN choice: INNER. We start from the aggregated blocker counts, so only
        users who logged at least one blocker appear — a "most blockers" board
        shouldn't list people at zero. (To include zero-blocker users you'd flip
        it to ``users LEFT JOIN weekly_blockers``.)
        """
        # Inclusive rolling window: `days` calendar days up to and including today
        # (days=7 -> today and the previous 6 days). Bound param -> no injection.
        week_start = date.today() - timedelta(days=days - 1)

        # Step 1 (the CTE): per-user blocker tally over the window.
        weekly_blockers = (
            select(
                PulseEntry.user_id.label("user_id"),
                func.count().label("blocker_count"),
            )
            .where(PulseEntry.has_blocker.is_(True))
            .where(PulseEntry.pulse_date >= week_start)
            .group_by(PulseEntry.user_id)
            .cte("weekly_blockers")
        )

        # Step 2: JOIN the tally to users to attach human-readable names, ranked.
        stmt = (
            select(
                weekly_blockers.c.user_id,
                User.display_name,
                weekly_blockers.c.blocker_count,
            )
            .select_from(weekly_blockers)
            .join(User, User.id == weekly_blockers.c.user_id)
            # Rank by count; tie-break on name so the output is deterministic
            # (otherwise tied users come back in arbitrary order).
            .order_by(weekly_blockers.c.blocker_count.desc(), User.display_name.asc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        return [TopBlockerRow(**row._mapping) for row in result.all()]
