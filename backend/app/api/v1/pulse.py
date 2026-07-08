"""Pulse check-in endpoints."""

from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.pulse import PulseCreate, PulseResponse, PulseTeamResponse
from app.services.pulse_service import PulseService

router = APIRouter()


@router.post(
    "",
    response_model=PulseResponse,
    status_code=201,
    responses={409: {"description": "User already submitted a pulse today"}},
)
async def submit_pulse(
    payload: PulseCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> PulseResponse:
    """Submit a daily pulse check-in (mood, energy, blocker flag).

    201 on success; 422 on invalid mood/energy (schema-validated); 409 if the
    user already submitted today (raised by the service).
    """
    service = PulseService(db)
    return await service.create_pulse(current_user.id, payload)


@router.get("/me", response_model=list[PulseResponse])
async def get_my_pulses(
    db: DbSession,
    current_user: CurrentUser,
    limit: int = Query(30, ge=1, le=100, description="Max entries to return (1-100)"),
) -> list[PulseResponse]:
    """Get the current user's pulse history.

    An out-of-range limit (e.g. -5 or 0) is bad input -> 422, not a silent 200.
    An empty history is a valid result -> 200 with [].
    """
    service = PulseService(db)
    return await service.get_user_pulses(current_user.id, limit=limit)


@router.get(
    "/summary",
    response_model=PulseTeamResponse,
    responses={400: {"description": "target_date is in the future"}},
)
async def get_pulse_summary(
    db: DbSession,
    current_user: CurrentUser,
    scope: Literal["team"] = "team",
    target_date: date | None = None,
) -> PulseTeamResponse:
    """Get an aggregated pulse summary (defaults to today's team summary).

    ``scope`` is a query-string filter (currently only ``team``) so future
    scopes can be added without minting a new URL.
    """
    # A future date can't have data yet -> that's bad input, not an empty success.
    if target_date is not None and target_date > date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_date cannot be in the future",
        )

    service = PulseService(db)
    return await service.get_team_summary(target_date)
