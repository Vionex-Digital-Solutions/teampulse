"""User profile endpoints."""

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: CurrentUser,
) -> UserResponse:
    """Get the current user's profile."""
    raise NotImplementedError("Sprint 1: implement profile retrieval")


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    payload: UserUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> UserResponse:
    """Update the current user's profile (display name, avatar, locale)."""
    raise NotImplementedError("Sprint 1: implement profile update")
