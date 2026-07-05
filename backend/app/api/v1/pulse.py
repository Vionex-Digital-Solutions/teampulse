"""Pulse check-in endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.pulse import PulseCreate, PulseResponse, PulseTeamResponse
from app.services.pulse_service import PulseAlreadyExistsError, PulseService

router = APIRouter()


@router.post("", response_model=PulseResponse, status_code=201)
async def submit_pulse(
    payload: PulseCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> PulseResponse:
    """Submit a daily pulse check-in (mood, energy, blocker flag)."""
    service = PulseService(db)
    try:
        return await service.create_pulse(current_user.id, payload)
    except PulseAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


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
