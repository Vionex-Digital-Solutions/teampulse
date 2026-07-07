"""DataLoaders that batch related-row lookups to avoid the N+1 problem.

A GraphQL query like ``kudosFeed { sender { displayName } }`` resolves the
``sender`` field once *per kudos row*. Done naively that is one ``SELECT`` per
row (the classic N+1). A DataLoader instead collects every ``sender_id``
requested within a single tick of the event loop and resolves them all in one
batched ``WHERE id IN (...)`` query.

The loader caches per instance, so it must be created **per request** (see
``context.build_context``) — never share one across requests, or you would leak
one user's data into another's response.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from strawberry.dataloader import DataLoader

from app.models.user import User


def build_user_loader(db: AsyncSession) -> DataLoader[uuid.UUID, User | None]:
    """Build a DataLoader that batch-loads users by id for the given session."""

    async def load_users(user_ids: list[uuid.UUID]) -> list[User | None]:
        # One query for the whole batch of ids Strawberry asked for this tick.
        result = await db.execute(select(User).where(User.id.in_(user_ids)))
        by_id = {user.id: user for user in result.scalars().all()}
        # DataLoader requires the results line up 1:1 with the input keys, in
        # order. Missing ids resolve to None rather than dropping out.
        return [by_id.get(user_id) for user_id in user_ids]

    return DataLoader(load_fn=load_users)
