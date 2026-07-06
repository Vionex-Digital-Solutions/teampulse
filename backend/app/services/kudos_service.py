"""Business logic for the kudos feed, including cursor pagination."""

import base64
import binascii
import uuid
from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kudos import Kudos
from app.schemas.kudos import KudosFeedPage, KudosResponse


class InvalidCursorError(Exception):
    """Raised when a caller supplies a cursor we can't decode."""


# A cursor points at the last row of the page the caller already has. We sort
# the feed by (created_at DESC, id DESC): created_at is the natural "newest
# first" order, and id is the tie-breaker so rows sharing a timestamp still
# have one stable, total order. The cursor therefore has to carry BOTH values.
def _encode_cursor(created_at: datetime, kudos_id: uuid.UUID) -> str:
    """Pack (created_at, id) into one opaque, URL-safe token."""
    raw = f"{created_at.isoformat()}|{kudos_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """Reverse _encode_cursor, rejecting anything malformed with a 400-able error."""
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        created_at_str, id_str = raw.split("|", 1)
        return datetime.fromisoformat(created_at_str), uuid.UUID(id_str)
    except (ValueError, binascii.Error) as exc:
        # We never want a bad cursor to 500 — it's a client-side mistake.
        raise InvalidCursorError("Malformed pagination cursor.") from exc


class KudosService:
    """Service for reading and writing kudos entries."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_feed(
        self, limit: int, cursor: str | None = None
    ) -> KudosFeedPage:
        """Return one page of the team kudos feed, newest first.

        Keyset (cursor) pagination: instead of OFFSET N — which makes the DB
        walk and throw away N rows and can skip/repeat items when new kudos
        arrive mid-scroll — we remember the last row seen and ask for the rows
        strictly "after" it in our sort order.
        """
        stmt = select(Kudos).order_by(Kudos.created_at.desc(), Kudos.id.desc())

        if cursor is not None:
            after_created_at, after_id = _decode_cursor(cursor)
            # Row-value keyset predicate: take rows older than the cursor, or
            # same timestamp but a smaller id (our DESC tie-break). This is the
            # tuple comparison (created_at, id) < (cursor_created_at, cursor_id)
            # written out explicitly so it works the same on SQLite and Postgres.
            stmt = stmt.where(
                or_(
                    Kudos.created_at < after_created_at,
                    and_(
                        Kudos.created_at == after_created_at,
                        Kudos.id < after_id,
                    ),
                )
            )

        # Fetch one extra row: if it comes back, we know a next page exists and
        # the extra row's key becomes the next cursor. Then we drop it.
        result = await self.db.execute(stmt.limit(limit + 1))
        rows = list(result.scalars().all())

        has_more = len(rows) > limit
        page_rows = rows[:limit]

        next_cursor: str | None = None
        if has_more:
            last = page_rows[-1]
            next_cursor = _encode_cursor(last.created_at, last.id)

        return KudosFeedPage(
            items=[KudosResponse.model_validate(row) for row in page_rows],
            next_cursor=next_cursor,
        )
