"""Kudos (peer recognition) endpoints."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.kudos import Kudos
from app.models.user import User
from app.schemas.kudos import KudosCreate, KudosResponse

router = APIRouter()


@router.post("", response_model=KudosResponse, status_code=201)
async def send_kudos(
    payload: KudosCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> KudosResponse:
    """Send a kudos to a teammate."""
    # You can't give kudos to yourself.
    if payload.receiver_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot send kudos to yourself.",
        )

    # Make sure the receiver actually exists and is an active teammate.
    result = await db.execute(select(User).where(User.id == payload.receiver_id))
    receiver = result.scalar_one_or_none()
    if receiver is None or not receiver.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receiver not found.",
        )

    # Build the ORM row. The sender is always the authenticated user — we never
    # trust a client-supplied sender_id. category is an Enum, so take its value.
    kudos = Kudos(
        sender_id=current_user.id,
        receiver_id=payload.receiver_id,
        category=payload.category.value,
        message=payload.message,
        message_ar=payload.message_ar,
    )

    db.add(kudos)
    await db.commit()
    # Reload so server/Python-side defaults (id, created_at) are populated
    # before we serialize the response.
    await db.refresh(kudos)

    return kudos


@router.get("/feed", response_model=list[KudosResponse])
async def get_kudos_feed(
    db: DbSession,
    current_user: CurrentUser,
    limit: int = 50,
    offset: int = 0,
) -> list[KudosResponse]:
    """Get the public kudos feed for the team."""
    # Newest kudos first, with pagination via limit/offset.
    result = await db.execute(
        select(Kudos)
        .order_by(Kudos.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())
