"""Integration tests for the resumes router (wave 4).

The upload path is exercised with a text file (no PDF dependency in the test
harness); resume_parser falls back to UTF-8 decode for non-PDF input.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from tests.helpers import auth_headers, register_test_user


@pytest.mark.asyncio
async def test_resume_upload_extracts_skills(client: AsyncClient) -> None:
    _, token, cleanup = await register_test_user(client, role="seeker")
    headers = auth_headers(token)
    try:
        body = (
            "Experienced backend engineer with Python, FastAPI, PostgreSQL and "
            "Docker. Some Kubernetes exposure."
        )
        resp = await client.post(
            "/resumes/upload",
            params={"name": "main"},
            files={"file": ("cv.txt", body.encode("utf-8"), "text/plain")},
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        out = resp.json()
        assert out["name"] == "main"
        # parsed_skills is a comma-separated string.
        skills = {s.strip() for s in out["parsed_skills"].split(",") if s.strip()}
        assert {"python", "fastapi", "postgresql", "docker"} <= skills
    finally:
        await cleanup()


@pytest.mark.asyncio
async def test_resume_upload_rejects_empty_file(client: AsyncClient) -> None:
    _, token, cleanup = await register_test_user(client, role="seeker")
    try:
        resp = await client.post(
            "/resumes/upload",
            params={"name": "blank"},
            files={"file": ("blank.txt", b"", "text/plain")},
            headers=auth_headers(token),
        )
        assert resp.status_code == 400
    finally:
        await cleanup()


@pytest.mark.asyncio
async def test_resume_versions_create_and_list(client: AsyncClient) -> None:
    _, token, cleanup = await register_test_user(client, role="seeker")
    headers = auth_headers(token)
    try:
        v1 = await client.post(
            "/resumes/versions",
            json={
                "name": "Backend variant",
                "target_role": "Senior Python",
                "content": {"summary": "10 years backend"},
            },
            headers=headers,
        )
        assert v1.status_code == 201
        assert v1.json()["content"] == {"summary": "10 years backend"}

        v2 = await client.post(
            "/resumes/versions",
            json={
                "name": "Data variant",
                "target_role": "Data Engineer",
                "content": {"summary": "ETL, dbt, airflow"},
            },
            headers=headers,
        )
        assert v2.status_code == 201

        listing = await client.get("/resumes/versions", headers=headers)
        assert listing.status_code == 200
        names = [item["name"] for item in listing.json()]
        # Newest first.
        assert names[0] == "Data variant"
        assert "Backend variant" in names
    finally:
        await cleanup()


@pytest.mark.asyncio
async def test_employer_cannot_use_resume_endpoints(client: AsyncClient) -> None:
    _, token, cleanup = await register_test_user(client, role="employer")
    try:
        upload = await client.post(
            "/resumes/upload",
            params={"name": "x"},
            files={"file": ("x.txt", b"python", "text/plain")},
            headers=auth_headers(token),
        )
        assert upload.status_code == 403

        ver = await client.post(
            "/resumes/versions",
            json={"name": "x", "target_role": "", "content": {}},
            headers=auth_headers(token),
        )
        assert ver.status_code == 403

        listing = await client.get(
            "/resumes/versions", headers=auth_headers(token)
        )
        assert listing.status_code == 403
    finally:
        await cleanup()


@pytest.mark.asyncio
async def test_resume_improve_returns_suggestions(client: AsyncClient) -> None:
    """``POST /resumes/versions/{id}/improve`` returns summary + suggestions.

    In CI we have no ``ANTHROPIC_API_KEY`` so this exercises the rule-based
    backend; both the shape of the response and the budget-decrement
    behaviour are still meaningful — the route layer is the same.
    """
    _, token, cleanup = await register_test_user(client, role="seeker")
    headers = auth_headers(token)
    try:
        # Create a version with a deliberately thin payload — the rule-
        # based backend should detect missing skills/experience and surface
        # concrete suggestions.
        created = await client.post(
            "/resumes/versions",
            json={
                "name": "Sparse variant",
                "target_role": "Senior Python",
                "content": {"summary": "ok"},
            },
            headers=headers,
        )
        assert created.status_code == 201
        version_id = created.json()["id"]

        resp = await client.post(
            f"/resumes/versions/{version_id}/improve",
            json={"target_role": "Senior Python", "focus": "ML фокус"},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert isinstance(body["summary"], str) and body["summary"].strip()
        assert isinstance(body["suggestions"], list) and body["suggestions"]
        assert body["used_today"] >= 1
        assert body["limit"] >= body["used_today"]
        assert body["backend"] in {"anthropic", "rule_based"}
    finally:
        await cleanup()


@pytest.mark.asyncio
async def test_resume_improve_unknown_version_is_404(client: AsyncClient) -> None:
    """Improving a version that doesn't exist (or belongs to someone else) is 404."""
    _, token, cleanup = await register_test_user(client, role="seeker")
    try:
        resp = await client.post(
            "/resumes/versions/999999/improve",
            json={"target_role": "", "focus": ""},
            headers=auth_headers(token),
        )
        assert resp.status_code == 404
    finally:
        await cleanup()


@pytest.mark.asyncio
async def test_resume_improve_rejects_employer(client: AsyncClient) -> None:
    """Employers cannot touch /resumes/versions/{id}/improve."""
    _, token, cleanup = await register_test_user(client, role="employer")
    try:
        resp = await client.post(
            "/resumes/versions/1/improve",
            json={"target_role": "", "focus": ""},
            headers=auth_headers(token),
        )
        # 403 (role check) takes precedence over 404 (version lookup).
        assert resp.status_code == 403
    finally:
        await cleanup()
