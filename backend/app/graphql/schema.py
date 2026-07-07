"""Strawberry GraphQL schema: a read-only ``kudosFeed`` query.

This sits *next to* the REST API — it does not replace it. It exposes the same
kudos data as ``GET /api/v1/kudos/feed``, but lets the client pick exactly which
fields (and which nested ``sender`` fields) it wants in a single request.

Field names are auto-converted to camelCase in the GraphQL schema, so
``display_name`` is queried as ``displayName``, ``kudos_feed`` as ``kudosFeed``,
etc.
"""

import uuid
from datetime import datetime
from typing import Annotated, Any

import strawberry
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from graphql import GraphQLError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info

from app.api.deps import DbSession
from app.core.security import decode_access_token
from app.graphql.dataloaders import build_user_loader
from app.models.kudos import Kudos
from app.models.user import User

# --- Types -----------------------------------------------------------------


@strawberry.type
class UserType:
    """A user, exposed only as the author of a kudos (the nested ``sender``)."""

    id: uuid.UUID
    display_name: str

    @classmethod
    def from_model(cls, user: User) -> "UserType":
        return cls(id=user.id, display_name=user.display_name)


@strawberry.type
class KudosType:
    """A single kudos entry. Scalars come straight off the row; ``sender`` is a
    nested type resolved lazily so the client only pays for it when requested."""

    id: uuid.UUID
    message: str
    message_ar: str | None
    category: str
    created_at: datetime
    # sender_id is kept on the object so the sender resolver can batch-load with
    # it. It is also a perfectly good scalar to expose for REST parity.
    sender_id: uuid.UUID
    receiver_id: uuid.UUID

    @classmethod
    def from_model(cls, kudos: Kudos) -> "KudosType":
        return cls(
            id=kudos.id,
            message=kudos.message,
            message_ar=kudos.message_ar,
            category=kudos.category,
            created_at=kudos.created_at,
            sender_id=kudos.sender_id,
            receiver_id=kudos.receiver_id,
        )

    @strawberry.field
    async def sender(self, info: Info) -> UserType | None:
        """Resolve the kudos author.

        Uses the per-request DataLoader so that N kudos in the feed cause a
        single batched user query, not N separate ones.
        """
        loader = info.context["user_loader"]
        user = await loader.load(self.sender_id)
        return UserType.from_model(user) if user is not None else None


# --- Query -----------------------------------------------------------------


def _require_user(info: Info) -> User:
    """Enforce auth inside the resolver (not at the HTTP layer).

    Doing the check here — rather than in ``build_context`` — is what lets the
    GraphiQL explorer page load without a token. An unauthenticated *query*
    still fails, mirroring the REST feed's Bearer requirement.
    """
    user: User | None = info.context["current_user"]
    if user is None or not user.is_active:
        raise GraphQLError("Not authenticated")
    return user


@strawberry.type
class Query:
    @strawberry.field
    async def kudos_feed(
        self,
        info: Info,
        limit: int = 50,
        offset: int = 0,
    ) -> list[KudosType]:
        """The team kudos feed, newest first — the GraphQL twin of
        ``GET /api/v1/kudos/feed``."""
        _require_user(info)

        # Clamp to the same bounds the REST endpoint enforces via Query(...).
        limit = max(1, min(limit, 100))
        offset = max(0, offset)

        db: AsyncSession = info.context["db"]
        result = await db.execute(
            select(Kudos)
            .order_by(Kudos.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [KudosType.from_model(k) for k in result.scalars().all()]


schema = strawberry.Schema(query=Query)


# --- Context + router ------------------------------------------------------


# auto_error=False so a tokenless request (e.g. loading the GraphiQL page in a
# browser) is not rejected at the HTTP layer; the resolver enforces auth.
_optional_bearer = HTTPBearer(auto_error=False)


async def get_optional_user(
    db: DbSession,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_optional_bearer)
    ],
) -> User | None:
    """Resolve the caller from a Bearer token, or ``None`` if absent/invalid.

    This is the tokenless-friendly sibling of the REST ``CurrentUser``
    dependency — it never raises, so the GraphiQL explorer can load. Whether a
    valid user is actually required is decided per-resolver (see
    ``_require_user``).
    """
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(str(payload.get("sub")))
    except Exception:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


OptionalUser = Annotated["User | None", Depends(get_optional_user)]


async def build_context(
    db: DbSession,
    current_user: OptionalUser,
) -> dict[str, Any]:
    """Per-request GraphQL context.

    Reuses the existing ``DbSession`` dependency verbatim for the shared async
    session. Auth is resolved optionally here and enforced in the resolver, so
    the explorer page still loads without a token. The DataLoader is built here
    so it lives for exactly one request.
    """
    return {
        "db": db,
        "current_user": current_user,
        "user_loader": build_user_loader(db),
    }


graphql_router: GraphQLRouter[dict[str, Any], None] = GraphQLRouter(
    schema, context_getter=build_context
)
