"""Team digest endpoints."""

from typing import Literal

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession

router = APIRouter()


@router.get("")
async def get_digest(
    db: DbSession,
    current_user: CurrentUser,
    period: Literal["weekly"] = "weekly",
) -> dict:
    """Get a team health digest for the given ``period`` (defaults to weekly).

    ``period`` is a query-string filter (currently only ``weekly``) so a daily
    or monthly digest never needs its own URL.
    """
    raise NotImplementedError("Sprint 3: implement weekly digest generation")
