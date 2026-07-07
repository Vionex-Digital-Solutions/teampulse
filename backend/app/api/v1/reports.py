"""Reporting endpoints (read-only team analytics)."""

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.schemas.report import TopBlockerRow
from app.services.report_service import ReportService

router = APIRouter()


@router.get(
    "/top-blockers",
    response_model=list[TopBlockerRow],
    summary="Teammates with the most blockers this week",
    description=(
        "Ranked report (highest first) of teammates who flagged the most "
        "blockers in a recent window. Built with a CTE that tallies blockers "
        "per user, then an INNER JOIN to `users` for display names.\n\n"
        "Any logged-in teammate can read this team report."
    ),
)
async def get_top_blockers(
    db: DbSession,
    current_user: CurrentUser,
    days: int = Query(7, ge=1, le=90, description="Window size in days (default 7)."),
    limit: int = Query(10, ge=1, le=100, description="Max rows to return (1-100)."),
) -> list[TopBlockerRow]:
    """Return the most-blocked teammates over the last ``days`` days."""
    service = ReportService(db)
    return await service.get_top_blockers(days=days, limit=limit)
