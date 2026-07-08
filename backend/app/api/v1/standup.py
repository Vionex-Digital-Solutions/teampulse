"""Async standup endpoints."""

from typing import Literal

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


@router.get("", response_model=list[StandupResponse])
async def get_standups(
    db: DbSession,
    current_user: CurrentUser,
    scope: Literal["team"] = "team",
) -> list[StandupResponse]:
    """List standup entries, filtered by ``scope`` (defaults to today's team).

    ``scope`` is a query-string filter (currently only ``team``) rather than a
    separate ``/team`` URL.
    """
    raise NotImplementedError("Sprint 1: implement team standup retrieval")
