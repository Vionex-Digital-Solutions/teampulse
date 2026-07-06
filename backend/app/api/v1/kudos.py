"""Kudos (peer recognition) endpoints."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.kudos import (
    DEFAULT_FEED_LIMIT,
    MAX_FEED_LIMIT,
    KudosCreate,
    KudosFeedPage,
    KudosResponse,
)
from app.services.kudos_service import InvalidCursorError, KudosService

router = APIRouter()


@router.post("", response_model=KudosResponse, status_code=201)
async def send_kudos(
    payload: KudosCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> KudosResponse:
    """Send a kudos to a teammate."""
    raise NotImplementedError("Sprint 2: implement kudos creation")


@router.get("/feed", response_model=KudosFeedPage)
async def get_kudos_feed(
    db: DbSession,
    current_user: CurrentUser,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=MAX_FEED_LIMIT,
            description="How many kudos to return (1-100).",
        ),
    ] = DEFAULT_FEED_LIMIT,
    cursor: Annotated[
        str | None,
        Query(description="Opaque cursor from a previous page's next_cursor."),
    ] = None,
) -> KudosFeedPage:
    """Get the public kudos feed for the team, newest first (cursor-paginated)."""
    service = KudosService(db)
    try:
        return await service.get_feed(limit=limit, cursor=cursor)
    except InvalidCursorError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
