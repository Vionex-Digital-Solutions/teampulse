"""Shared FastAPI dependencies for injection into route handlers."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.security import decode_access_token
from app.models.user import User

security_scheme = HTTPBearer()

DbSession = Annotated[AsyncSession, Depends(get_async_session)]


async def _user_from_token(db: AsyncSession, token: str) -> User:
    """Validate a JWT and load its active user, or raise the right HTTP error.

    Shared by the header-based and query-param-based auth dependencies so the
    validation rules (bad token -> 401, unknown user -> 404, deactivated ->
    403) live in exactly one place.
    """
    try:
        payload = decode_access_token(token)
        subject = payload.get("sub")
        if subject is None:
            raise ValueError("missing subject")
        # The JWT subject is a string; User.id is a UUID column, so convert
        # before querying (comparing the column to a raw str raises).
        user_id = UUID(str(subject))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )
    return user


async def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security_scheme)],
) -> User:
    """Extract and validate the current user from the JWT Bearer token."""
    return await _user_from_token(db, credentials.credentials)


async def get_current_user_from_query(
    db: DbSession,
    token: Annotated[
        str,
        Query(
            description=(
                "JWT access token. Sent as a query param (not an "
                "`Authorization` header) because the browser `EventSource` API "
                "used for SSE cannot set request headers."
            ),
        ),
    ],
) -> User:
    """Authenticate via a ``?token=`` query param, for SSE/streaming endpoints.

    Browser ``EventSource`` cannot send an ``Authorization`` header, so the
    live-feed endpoint passes the JWT in the URL instead. Validation is
    otherwise identical to :func:`get_current_user`.
    """
    return await _user_from_token(db, token)


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentUserFromQuery = Annotated[User, Depends(get_current_user_from_query)]
