"""Integration tests for the vacancies router (wave 3).

Exercises employer-only role gating, CRUD, ownership enforcement, archival
toggles, promotion, action logging, and pagination.  Live hh.ru fetch is
disabled via the ``include_live_hh=False`` query flag so the suite stays
hermetic.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from tests.helpers import auth_headers, register_test_user


@pytest.mark.asyncio
async def test_seeker_cannot_create_vacancy(client: AsyncClient) -> None:
    _, token, cleanup = await register_test_user(client, role="seeker")
    try:
        resp = await client.post(
            "/vacancies",
            json={
                "source": "manual",
                "external_id": "test-1",
                "title": "Backend Engineer",
                "company": "Otklik",
                "location": "Moscow",
            },
            headers=auth_headers(token),
        )
        assert resp.status_code == 403
    finally:
        await cleanup()


@pytest.mark.asyncio
async def test_employer_vacancy_lifecycle(client: AsyncClient) -> None:
    _, token, cleanup = await register_test_user(client, role="employer")
    headers = auth_headers(token)
    try:
        # Create
        create = await client.post(
            "/vacancies",
            json={
                "source": "manual",
                "external_id": "wave3-1",
                "title": "Senior Python Engineer",
                "company": "Otklik",
                "location": "Remote",
                "salary_from": 250000,
                "salary_to": 400000,
                "description": "FastAPI, async, postgres",
            },
            headers=headers,
        )
        assert create.status_code == 201, create.text
        vacancy = create.json()
        vid = vacancy["id"]
        assert vacancy["title"] == "Senior Python Engineer"
        assert vacancy["is_active"] is True

        # Update
        upd = await client.put(
            f"/vacancies/{vid}",
            json={"title": "Lead Python Engineer", "applications_count": 3},
            headers=headers,
        )
        assert upd.status_code == 200
        assert upd.json()["title"] == "Lead Python Engineer"
        assert upd.json()["applications_count"] == 3

        # My listing (hermetic — no live hh)
        mine = await client.get("/vacancies/my", headers=headers)
        assert mine.status_code == 200
        my_ids = [v["id"] for v in mine.json()]
        assert vid in my_ids

        # Paged listing
        page = await client.get(
            "/vacancies/my/page", headers=headers, params={"page_size": 5}
        )
        assert page.status_code == 200
        page_body = page.json()
        assert page_body["page"] == 1
        assert page_body["total"] >= 1
        assert any(item["id"] == vid for item in page_body["items"])

        # Analytics
        analytics = await client.get("/vacancies/my/analytics", headers=headers)
        assert analytics.status_code == 200
        assert analytics.json()["total"] >= 1
        assert analytics.json()["active"] >= 1

        # Archive → unpublish
        arch = await client.post(f"/vacancies/{vid}/archive", headers=headers)
        assert arch.status_code == 200
        assert arch.json()["status"] == "archived"
        archived_check = await client.get(
            "/vacancies/my", headers=headers, params={"status": "archived"}
        )
        assert any(v["id"] == vid for v in archived_check.json())

        # Publish (un-archive)
        pub = await client.post(f"/vacancies/{vid}/publish", headers=headers)
        assert pub.status_code == 200
        assert pub.json()["status"] == "published"

        # Promote
        promo = await client.post(
            f"/vacancies/{vid}/promote", json={"days": 3}, headers=headers
        )
        assert promo.status_code == 200
        assert promo.json()["status"] == "promoted"

        # Public listing finds it
        listing = await client.get(
            "/vacancies", params={"include_live_hh": "false"}
        )
        assert listing.status_code == 200
        assert any(item["id"] == vid for item in listing.json())

        # Action log accumulated multiple entries
        log = await client.get("/vacancies/my/actions", headers=headers)
        assert log.status_code == 200
        actions = [item["action"] for item in log.json()]
        assert "vacancy_created" in actions
        assert "vacancy_updated" in actions
        assert "vacancy_archived" in actions
        assert "vacancy_published" in actions
        assert "vacancy_promoted" in actions

        # CSV export
        export = await client.get(
            "/vacancies/my/actions/export", headers=headers
        )
        assert export.status_code == 200
        assert export.headers["content-type"].startswith("text/csv")
        assert "vacancy_created" in export.text

        # Soft delete
        delete_resp = await client.delete(f"/vacancies/{vid}", headers=headers)
        assert delete_resp.status_code == 200
        assert delete_resp.json()["status"] == "soft_deleted"

        post_delete = await client.get(
            "/vacancies", params={"include_live_hh": "false"}
        )
        assert all(item["id"] != vid for item in post_delete.json())
    finally:
        await cleanup()


@pytest.mark.asyncio
async def test_employer_cannot_touch_others_vacancies(client: AsyncClient) -> None:
    _, token_a, cleanup_a = await register_test_user(client, role="employer")
    _, token_b, cleanup_b = await register_test_user(client, role="employer")
    try:
        create = await client.post(
            "/vacancies",
            json={
                "source": "manual",
                "external_id": "wave3-cross",
                "title": "DevOps",
                "company": "Otklik",
                "location": "Moscow",
            },
            headers=auth_headers(token_a),
        )
        assert create.status_code == 201
        vid = create.json()["id"]

        # B should not be able to update A's vacancy.
        attempt = await client.put(
            f"/vacancies/{vid}",
            json={"title": "Hijacked"},
            headers=auth_headers(token_b),
        )
        assert attempt.status_code == 404

        # B can't archive it either.
        attempt2 = await client.post(
            f"/vacancies/{vid}/archive", headers=auth_headers(token_b)
        )
        assert attempt2.status_code == 404
    finally:
        await cleanup_a()
        await cleanup_b()


@pytest.mark.asyncio
async def test_invalid_work_mode_returns_400(client: AsyncClient) -> None:
    resp = await client.get(
        "/vacancies",
        params={"work_mode": "underwater", "include_live_hh": "false"},
    )
    assert resp.status_code == 400
