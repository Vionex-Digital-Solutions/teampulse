"""Kudos (peer recognition) endpoints."""

import asyncio
from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.api.deps import CurrentUser, CurrentUserFromQuery, DbSession
from app.models.kudos import Kudos
from app.models.user import User
from app.schemas.kudos import KudosCreate, KudosResponse
from app.services.kudos_broadcaster import broadcaster

router = APIRouter()

# How long the stream waits for a new kudos before sending a keep-alive comment.
# Keeps the connection alive through proxies and lets us re-check for client
# disconnects periodically.
_SSE_KEEPALIVE_SECONDS = 15


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

    # Fan the new kudos out to anyone watching the live SSE feed. We serialize
    # through KudosResponse so the pushed event has the exact same shape (and
    # JSON encoding of UUIDs/timestamps) as the REST responses.
    broadcaster.publish(KudosResponse.model_validate(kudos).model_dump_json())

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


@router.get(
    "/stream",
    summary="Stream the live kudos feed (Server-Sent Events)",
    description=(
        "Open a long-lived Server-Sent Events (SSE) connection that pushes "
        "each new kudos the moment it is created — no polling.\n\n"
        "Each event's `data:` line is a JSON kudos object with the same shape "
        "as `GET /kudos/feed` items. Only kudos created *after* you connect are "
        "sent; use `GET /kudos/feed` first to load the existing history.\n\n"
        "**Subscribing from a browser:**\n"
        "```js\n"
        "const es = new EventSource(`/api/v1/kudos/stream?token=${jwt}`);\n"
        "es.onmessage = (e) => addToFeed(JSON.parse(e.data));\n"
        "```\n"
        "The browser reconnects automatically if the connection drops.\n\n"
        "**Watching from the terminal:**\n"
        "```\n"
        "curl -N 'http://localhost:8000/api/v1/kudos/stream?token=<JWT>'\n"
        "```\n\n"
        "**Auth:** the JWT is passed as the `token` query param (not an "
        "`Authorization` header) because the `EventSource` API cannot set "
        "headers. Get a token from `POST /api/v1/auth/login`."
    ),
    responses={
        200: {
            "description": "An open SSE stream of kudos events.",
            "content": {"text/event-stream": {}},
        },
        401: {
            "description": "Missing or invalid token.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid or expired token"}
                }
            },
        },
    },
)
async def stream_kudos(
    request: Request,
    current_user: CurrentUserFromQuery,
) -> StreamingResponse:
    """Stream newly created kudos to the client over SSE."""

    async def event_generator() -> AsyncGenerator[str, None]:
        # subscribe() registers our queue and — crucially — removes it again
        # when the client disconnects and this generator is torn down.
        async with broadcaster.subscribe() as queue:
            while True:
                # Stop cleanly if the client has gone away.
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(
                        queue.get(), timeout=_SSE_KEEPALIVE_SECONDS
                    )
                except TimeoutError:
                    # No kudos for a while: send a comment line (starts with
                    # ':') as a heartbeat. Clients ignore it; it keeps proxies
                    # from closing an idle connection.
                    yield ": keep-alive\n\n"
                    continue
                # SSE wire format: 'data: <payload>' then a blank line.
                yield f"data: {data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            # Tell nginx (if present) not to buffer the stream.
            "X-Accel-Buffering": "no",
        },
    )
