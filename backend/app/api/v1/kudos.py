"""Kudos (peer recognition) endpoints."""

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.kudos import KudosCreate, KudosResponse

router = APIRouter()


@router.post("", response_model=KudosResponse, status_code=201)
async def send_kudos(
    payload: KudosCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> KudosResponse:
    """Send a kudos to a teammate."""
    raise NotImplementedError("Sprint 2: implement kudos creation")


@router.get("/feed", response_model=list[KudosResponse])
async def get_kudos_feed(
    db: DbSession,
    current_user: CurrentUser,
    limit: int = 50,
    offset: int = 0,
) -> list[KudosResponse]:
    """Get the public kudos feed for the team."""
    raise NotImplementedError("Sprint 2: implement kudos feed")
