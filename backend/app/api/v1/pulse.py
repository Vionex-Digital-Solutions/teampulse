"""Pulse check-in endpoints."""

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.pulse import PulseCreate, PulseResponse, PulseTeamResponse

router = APIRouter()


@router.post("", response_model=PulseResponse, status_code=201)
async def submit_pulse(
    payload: PulseCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> PulseResponse:
    """Submit a daily pulse check-in (mood, energy, blocker flag)."""
    raise NotImplementedError("Sprint 1: implement pulse submission")


@router.get("/me", response_model=list[PulseResponse])
async def get_my_pulses(
    db: DbSession,
    current_user: CurrentUser,
    limit: int = 30,
) -> list[PulseResponse]:
    """Get the current user's pulse history."""
    raise NotImplementedError("Sprint 1: implement my pulses retrieval")


@router.get("/team", response_model=PulseTeamResponse)
async def get_team_pulses(
    db: DbSession,
    current_user: CurrentUser,
) -> PulseTeamResponse:
    """Get aggregated pulse data for the team (today's summary)."""
    raise NotImplementedError("Sprint 1: implement team pulse aggregation")
