"""Kudos (peer recognition) endpoints."""

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.kudos import Kudos
from app.models.user import User
from app.schemas.kudos import KudosCreate, KudosResponse

router = APIRouter()


@router.post(
    "",
    response_model=KudosResponse,
    status_code=201,
    summary="Send kudos to a teammate",
    description=(
        "Give recognition to another active teammate.\n\n"
        "- The **sender is always you** (the authenticated user) — you never "
        "send a `sender_id`.\n"
        "- You **cannot** send kudos to yourself (returns `400`).\n"
        "- The receiver must be an existing, active user (otherwise `404`).\n\n"
        "On success, returns the created kudos entry including its generated "
        "`id` and `created_at`.\n\n"
        "**Auth:** requires a Bearer token. Get one from "
        "`POST /api/v1/auth/login`, then click **Authorize** (top right) and "
        "paste it — or send it yourself as `Authorization: Bearer <token>`."
    ),
    responses={
        201: {"description": "Kudos created successfully."},
        400: {
            "description": "You tried to send kudos to yourself.",
            "content": {
                "application/json": {
                    "example": {"detail": "You cannot send kudos to yourself."}
                }
            },
        },
        404: {
            "description": "The receiver does not exist or is not active.",
            "content": {
                "application/json": {"example": {"detail": "Receiver not found."}}
            },
        },
        401: {
            "description": "Missing or invalid authentication token.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid or expired token"}
                }
            },
        },
    },
)
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


@router.get(
    "/feed",
    response_model=list[KudosResponse],
    summary="Get the team kudos feed",
    description=(
        "Feed of all kudos for the team, visible to any logged-in teammate, "
        "**newest first**.\n\n"
        "Paginate with `limit` and `offset` — e.g. `?limit=20&offset=20` for "
        "the second page of 20. Returns an empty list when there are no more "
        "entries.\n\n"
        "**Auth:** requires a Bearer token. Get one from "
        "`POST /api/v1/auth/login`, then click **Authorize** (top right) and "
        "paste it — or send it yourself as `Authorization: Bearer <token>`."
    ),
    responses={
        200: {"description": "A list of kudos, newest first (may be empty)."},
        401: {
            "description": "Missing or invalid authentication token.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid or expired token"}
                }
            },
        },
    },
)
async def get_kudos_feed(
    db: DbSession,
    current_user: CurrentUser,
    limit: int = Query(
        50,
        ge=1,
        le=100,
        description="Maximum number of kudos to return (1–100).",
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of kudos to skip from the start, for pagination.",
    ),
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
