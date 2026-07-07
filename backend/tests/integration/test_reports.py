"""Tests for the reporting endpoints' query logic (JOIN + CTE).

Seeds known pulse data and asserts the 'top blockers this week' report ranks
users correctly, respects the time window, and excludes zero-blocker users
(the INNER JOIN behaviour). Seeds and queries through one session, so it needs
no HTTP round-trip and no session-commit override.
"""

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.pulse import PulseEntry
from app.models.user import User
from app.services.report_service import ReportService


def _user(name: str) -> User:
    return User(
        id=uuid.uuid4(),
        email=f"{name}@vionex.com",
        hashed_password=hash_password("testpass123"),
        display_name=name,
    )


def _pulse(user_id: uuid.UUID, on: date, *, blocker: bool) -> PulseEntry:
    return PulseEntry(
        user_id=user_id,
        pulse_date=on,
        mood=3,
        energy=3,
        has_blocker=blocker,
    )


@pytest.mark.asyncio
async def test_top_blockers_ranks_and_scopes_correctly(
    db_session: AsyncSession,
) -> None:
    today = date.today()
    alice, bob, carol = _user("Alice"), _user("Bob"), _user("Carol")
    db_session.add_all([alice, bob, carol])

    db_session.add_all([
        # Alice: 3 blockers inside the 7-day window (distinct days).
        _pulse(alice.id, today, blocker=True),
        _pulse(alice.id, today - timedelta(days=1), blocker=True),
        _pulse(alice.id, today - timedelta(days=2), blocker=True),
        # Alice: 1 blocker OUTSIDE the window -> must NOT be counted.
        _pulse(alice.id, today - timedelta(days=10), blocker=True),
        # Bob: 1 blocker inside the window.
        _pulse(bob.id, today, blocker=True),
        # Carol: a check-in but no blocker -> must NOT appear (INNER JOIN).
        _pulse(carol.id, today, blocker=False),
    ])
    await db_session.commit()

    rows = await ReportService(db_session).get_top_blockers(days=7, limit=10)

    # Ranked highest-first, zero-blocker Carol excluded, old blocker not counted.
    assert [(r.display_name, r.blocker_count) for r in rows] == [
        ("Alice", 3),
        ("Bob", 1),
    ]
    assert all(r.display_name != "Carol" for r in rows)


@pytest.mark.asyncio
async def test_top_blockers_empty_when_no_blockers(
    db_session: AsyncSession,
) -> None:
    dave = _user("Dave")
    db_session.add(dave)
    db_session.add(_pulse(dave.id, date.today(), blocker=False))
    await db_session.commit()

    rows = await ReportService(db_session).get_top_blockers(days=7, limit=10)
    assert rows == []


@pytest.mark.asyncio
async def test_top_blockers_respects_limit(db_session: AsyncSession) -> None:
    today = date.today()
    for i in range(5):
        u = _user(f"U{i}")
        db_session.add(u)
        db_session.add(_pulse(u.id, today, blocker=True))
    await db_session.commit()

    rows = await ReportService(db_session).get_top_blockers(days=7, limit=3)
    assert len(rows) == 3
