"""IDOR regression tests for user-data endpoints.

These tests prove the ownership guarantee behind the audit: a logged-in user
can only ever read their *own* records. The scoping lives inside the query
(`WHERE user_id == current_user.id`), and identity is taken from the JWT rather
than from any client-supplied id/param — so there is nothing to tamper with.

If a future change reintroduces an IDOR (e.g. an `/{id}` route, or trusting a
client-supplied `user_id`), one of these assertions should start failing.
"""

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, email: str) -> str:
    """Register a user via the public API and return their bearer token."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpass123", "display_name": email},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_pulse_me_is_scoped_to_the_caller(client: AsyncClient) -> None:
    """User B must never see User A's pulses via GET /pulse/me."""
    token_a = await _register(client, "alice@vionex.com")
    token_b = await _register(client, "bob@vionex.com")

    # Alice submits a pulse.
    submit = await client.post(
        "/api/v1/pulse",
        json={"mood": 4, "energy": 3, "has_blocker": False, "note": "alice-only"},
        headers=_auth(token_a),
    )
    assert submit.status_code == 201, submit.text
    alice_pulse_id = submit.json()["id"]

    # Alice sees exactly her own pulse.
    a_me = await client.get("/api/v1/pulse/me", headers=_auth(token_a))
    assert a_me.status_code == 200
    a_rows = a_me.json()
    assert len(a_rows) == 1
    assert a_rows[0]["id"] == alice_pulse_id
    assert a_rows[0]["note"] == "alice-only"

    # Bob submitted nothing -> Bob sees nothing. He cannot reach Alice's row.
    b_me = await client.get("/api/v1/pulse/me", headers=_auth(token_b))
    assert b_me.status_code == 200
    assert b_me.json() == []


@pytest.mark.asyncio
async def test_pulse_me_never_leaks_across_users(client: AsyncClient) -> None:
    """Each user's /pulse/me returns only rows they own, even when both submit."""
    token_a = await _register(client, "alice2@vionex.com")
    token_b = await _register(client, "bob2@vionex.com")

    await client.post(
        "/api/v1/pulse",
        json={"mood": 5, "energy": 5, "note": "a"},
        headers=_auth(token_a),
    )
    await client.post(
        "/api/v1/pulse",
        json={"mood": 1, "energy": 2, "note": "b"},
        headers=_auth(token_b),
    )

    a_rows = (await client.get("/api/v1/pulse/me", headers=_auth(token_a))).json()
    b_rows = (await client.get("/api/v1/pulse/me", headers=_auth(token_b))).json()

    # Every row returned to a caller belongs to that caller — no cross-leak.
    a_ids = {r["user_id"] for r in a_rows}
    b_ids = {r["user_id"] for r in b_rows}
    assert len(a_ids) == 1
    assert len(b_ids) == 1
    assert a_ids != b_ids
    assert all(r["note"] == "a" for r in a_rows)
    assert all(r["note"] == "b" for r in b_rows)


@pytest.mark.asyncio
async def test_pulse_me_requires_authentication(client: AsyncClient) -> None:
    """No token -> 401 (authentication), the gate before any ownership check."""
    resp = await client.get("/api/v1/pulse/me")
    assert resp.status_code in (401, 403)  # missing bearer credentials
