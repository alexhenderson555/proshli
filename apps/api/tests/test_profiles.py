"""Integration tests for the profiles router (wave 4).

Covers seeker + employer profile upsert (auto-create on first GET) and
cross-role role gating.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from tests.helpers import auth_headers, register_test_user


@pytest.mark.asyncio
async def test_seeker_profile_upsert(client: AsyncClient) -> None:
    _, token, cleanup = await register_test_user(client, role="seeker")
    headers = auth_headers(token)
    try:
        # GET auto-creates an empty record.
        first = await client.get("/profiles/seeker", headers=headers)
        assert first.status_code == 200
        assert first.json()["skills"] == []

        # PUT updates the persisted profile.
        upd = await client.put(
            "/profiles/seeker",
            json={
                "full_name": "Alex Test",
                "target_role": "Backend Engineer",
                "location": "Moscow",
                "about": "FastAPI fan",
                "skills": ["python", "postgres", "asyncio"],
            },
            headers=headers,
        )
        assert upd.status_code == 200
        body = upd.json()
        assert body["full_name"] == "Alex Test"
        assert body["skills"] == ["python", "postgres", "asyncio"]

        # Subsequent GET reflects the upsert.
        fetch = await client.get("/profiles/seeker", headers=headers)
        assert fetch.json()["target_role"] == "Backend Engineer"
    finally:
        await cleanup()


@pytest.mark.asyncio
async def test_employer_profile_upsert(client: AsyncClient) -> None:
    _, token, cleanup = await register_test_user(client, role="employer")
    headers = auth_headers(token)
    try:
        first = await client.get("/profiles/employer", headers=headers)
        assert first.status_code == 200
        assert first.json()["verified"] is False

        upd = await client.put(
            "/profiles/employer",
            json={
                "company_name": "Otklik",
                "website": "https://otklik.ai",
                "description": "Russian-language job aggregator",
            },
            headers=headers,
        )
        assert upd.status_code == 200
        assert upd.json()["company_name"] == "Otklik"

        fetch = await client.get("/profiles/employer", headers=headers)
        assert fetch.json()["website"] == "https://otklik.ai"
    finally:
        await cleanup()


@pytest.mark.asyncio
async def test_role_gating_on_profiles(client: AsyncClient) -> None:
    _, seeker_token, seeker_cleanup = await register_test_user(client, role="seeker")
    _, emp_token, emp_cleanup = await register_test_user(client, role="employer")
    try:
        # Seeker cannot touch employer profile.
        a = await client.get("/profiles/employer", headers=auth_headers(seeker_token))
        assert a.status_code == 403
        b = await client.put(
            "/profiles/employer",
            json={"company_name": "x", "website": "", "description": ""},
            headers=auth_headers(seeker_token),
        )
        assert b.status_code == 403

        # Employer cannot touch seeker profile.
        c = await client.get("/profiles/seeker", headers=auth_headers(emp_token))
        assert c.status_code == 403
        d = await client.put(
            "/profiles/seeker",
            json={
                "full_name": "x",
                "target_role": "",
                "location": "",
                "about": "",
                "skills": [],
            },
            headers=auth_headers(emp_token),
        )
        assert d.status_code == 403
    finally:
        await seeker_cleanup()
        await emp_cleanup()
