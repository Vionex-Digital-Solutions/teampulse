"""Weekly digest endpoints."""

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession

router = APIRouter()


@router.get("/weekly")
async def get_weekly_digest(
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Get the weekly team health digest with aggregated metrics."""
    raise NotImplementedError("Sprint 3: implement weekly digest generation")
