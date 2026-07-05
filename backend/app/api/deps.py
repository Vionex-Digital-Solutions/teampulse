"""Shared FastAPI dependencies for injection into route handlers."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.security import decode_access_token
from app.models.user import User

security_scheme = HTTPBearer()

DbSession = Annotated[AsyncSession, Depends(get_async_session)]


async def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security_scheme)],
) -> User:
    """Extract and validate the current user from the JWT Bearer token."""
    try:
        payload = decode_access_token(credentials.credentials)
        subject: str | None = payload.get("sub")
        if subject is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
            )
        # The JWT "sub" is a string, but User.id is a UUID column. Comparing a
        # str against the UUID type makes SQLAlchemy try str.hex and crash with
        # a 500, so parse it here — a malformed value is an invalid token (401).
        user_id = uuid.UUID(subject)
    except HTTPException:
        raise
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


CurrentUser = Annotated[User, Depends(get_current_user)]
