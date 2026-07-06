"""Injection-safety tests for the kudos endpoints.

These prove two things:

1. A SQL-injection payload sent as a kudos ``message`` is stored and returned
   as *literal text* — it is never executed, and the ``kudos`` table survives.
   This is what SQLAlchemy's parameterized queries buy us: data never becomes
   code.
2. Server-side validation rejects malformed input (bad category, blank message)
   with ``422`` before it ever reaches the database.
"""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.kudos import Kudos
from app.models.user import User

# A classic injection string: if the message were ever concatenated into raw
# SQL, this would try to drop the table. It must come back as plain text.
INJECTION_PAYLOAD = "Robert'); DROP TABLE kudos; --"


def _auth_header(user: User) -> dict[str, str]:
    """Build a Bearer header for a user, the same way login does."""
    token = create_access_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def receiver(db_session: AsyncSession) -> User:
    """A second user to receive kudos (you can't send kudos to yourself)."""
    user = User(
        id=uuid.uuid4(),
        email="receiver@vionex.com",
        hashed_password=hash_password("testpass123"),
        display_name="Receiver User",
        display_name_ar="مستلم",
        locale="en",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def test_injection_payload_stored_as_plain_text(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    receiver: User,
) -> None:
    """A malicious message is stored verbatim, and the table is untouched."""
    response = await client.post(
        "/api/v1/kudos",
        headers=_auth_header(test_user),
        json={
            "receiver_id": str(receiver.id),
            "category": "teamwork",
            "message": INJECTION_PAYLOAD,
        },
    )

    assert response.status_code == 201
    # The API echoes back the exact string it received — not executed, not mangled.
    assert response.json()["message"] == INJECTION_PAYLOAD

    # The table still exists and holds exactly one row: the DROP never ran.
    count = await db_session.scalar(select(func.count()).select_from(Kudos))
    assert count == 1

    # And the row on disk holds the literal payload, byte-for-byte.
    stored = await db_session.scalar(select(Kudos.message))
    assert stored == INJECTION_PAYLOAD


async def test_injection_in_category_is_rejected(
    client: AsyncClient,
    test_user: User,
    receiver: User,
) -> None:
    """A non-enum category (injection or otherwise) is a 422, never stored."""
    response = await client.post(
        "/api/v1/kudos",
        headers=_auth_header(test_user),
        json={
            "receiver_id": str(receiver.id),
            "category": "teamwork'; DROP TABLE kudos; --",
            "message": "hi",
        },
    )
    assert response.status_code == 422


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
async def test_blank_message_is_rejected(
    client: AsyncClient,
    test_user: User,
    receiver: User,
    blank: str,
) -> None:
    """Empty and whitespace-only messages are rejected by the validator."""
    response = await client.post(
        "/api/v1/kudos",
        headers=_auth_header(test_user),
        json={
            "receiver_id": str(receiver.id),
            "category": "teamwork",
            "message": blank,
        },
    )
    assert response.status_code == 422


async def test_message_is_trimmed(
    client: AsyncClient,
    test_user: User,
    receiver: User,
) -> None:
    """Surrounding whitespace is stripped before storage."""
    response = await client.post(
        "/api/v1/kudos",
        headers=_auth_header(test_user),
        json={
            "receiver_id": str(receiver.id),
            "category": "teamwork",
            "message": "  great work  ",
        },
    )
    assert response.status_code == 201
    assert response.json()["message"] == "great work"
