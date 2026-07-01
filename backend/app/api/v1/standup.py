"""Async standup endpoints."""

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.standup import StandupCreate, StandupResponse

router = APIRouter()


@router.post("", response_model=StandupResponse, status_code=201)
async def submit_standup(
    payload: StandupCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> StandupResponse:
    """Submit a daily async standup (yesterday, today, blockers)."""
    raise NotImplementedError("Sprint 1: implement standup submission")


@router.get("/team", response_model=list[StandupResponse])
async def get_team_standups(
    db: DbSession,
    current_user: CurrentUser,
) -> list[StandupResponse]:
    """Get today's standup entries for the whole team."""
    raise NotImplementedError("Sprint 1: implement team standup retrieval")
