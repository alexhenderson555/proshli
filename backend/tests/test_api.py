import time

from app.config import settings
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def unique_email(prefix: str) -> str:
    return f"{prefix}-{int(time.time() * 1000)}@jobskout.dev"


def register_user(role: str) -> str:
    email = unique_email(role)
    resp = client.post(
        "/auth/register",
        json={"email": email, "password": "strongpass1", "role": role},
    )
    assert resp.status_code == 201
    return resp.json()["access_token"]


def test_auth_and_me():
    token = register_user("seeker")
    resp = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "seeker"


def test_telegram_link_code_and_bot_login_flow():
    seeker_token = register_user("seeker")
    seeker_headers = {"Authorization": f"Bearer {seeker_token}"}
    bot_headers = {"x-bot-service-key": settings.bot_service_key}

    code_resp = client.post("/auth/telegram/link-code", headers=seeker_headers)
    assert code_resp.status_code == 200
    code = code_resp.json()["code"]
    assert code

    consume = client.post(
        "/auth/telegram/consume-link",
        headers=bot_headers,
        json={
            "code": code,
            "telegram_user_id": "555111",
            "telegram_chat_id": "777999",
            "telegram_username": "alex",
        },
    )
    assert consume.status_code == 200
    assert consume.json()["access_token"]

    login = client.post(
        "/auth/telegram/login",
        headers=bot_headers,
        json={"telegram_user_id": "555111", "telegram_chat_id": "777999"},
    )
    assert login.status_code == 200
    assert login.json()["access_token"]


def test_ai_guardrails_offtopic_rejected():
    token = register_user("seeker")
    resp = client.post(
        "/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": "расскажи анекдот про котов"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted"] is False
    assert "только по вопросам работы" in body["message"]


def test_ai_limit_enforced():
    token = register_user("seeker")
    old_limit = settings.ai_daily_request_limit
    settings.ai_daily_request_limit = 1
    try:
        first = client.post(
            "/ai/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "Ищу junior python вакансию"},
        )
        assert first.status_code == 200
        assert first.json()["accepted"] is True

        second = client.post(
            "/ai/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "Ищу еще варианты удаленки"},
        )
        assert second.status_code == 200
        assert second.json()["accepted"] is False
    finally:
        settings.ai_daily_request_limit = old_limit


def test_employer_can_ingest_and_create():
    employer_token = register_user("employer")
    h = {"Authorization": f"Bearer {employer_token}"}

    ingest = client.post("/ingest/hh", headers=h)
    assert ingest.status_code == 200
    assert ingest.json()["fetched_count"] >= 1
    first_inserted = ingest.json()["inserted_count"]

    ingest_again = client.post("/ingest/hh", headers=h)
    assert ingest_again.status_code == 200
    assert ingest_again.json()["inserted_count"] <= first_inserted
    assert ingest_again.json()["deduped_count"] >= 0

    create = client.post(
        "/vacancies",
        headers=h,
        json={
            "source": "manual",
            "external_id": f"manual-{int(time.time())}",
            "title": "QA Engineer",
            "company": "JobSkout",
            "location": "Remote",
            "employment_type": "full-time",
            "experience_level": "middle",
            "salary_from": 150000,
            "salary_to": 220000,
            "currency": "RUB",
            "description": "Testing, API, Playwright",
            "applications_count": 0,
        },
    )
    assert create.status_code == 201


def test_digest_preview_available():
    token = register_user("seeker")
    h = {"Authorization": f"Bearer {token}"}
    ingest_user = register_user("employer")
    client.post("/ingest/company_sites", headers={"Authorization": f"Bearer {ingest_user}"})

    preview = client.get("/digest/preview", headers=h)
    assert preview.status_code == 200
    body = preview.json()
    assert body["frequency"] in {"daily", "weekly"}
    assert isinstance(body["channels"], list)
    assert isinstance(body["items"], list)


def test_admin_scheduler_run_once():
    employer_token = register_user("employer")
    seeker_token = register_user("seeker")
    # Ensure seeker has preferences initialized.
    pref = client.put(
        "/digest/preferences",
        headers={"Authorization": f"Bearer {seeker_token}"},
        json={
            "frequency": "daily",
            "via_telegram": False,
            "via_email": True,
            "telegram_chat_id": None,
        },
    )
    assert pref.status_code == 200

    run = client.post("/admin/run-scheduler?frequency=daily", headers={"Authorization": f"Bearer {employer_token}"})
    assert run.status_code == 200
    body = run.json()
    assert body["ingestion_runs"] >= 2
    assert body["digests_sent"] >= 1
    assert "digests_failed" in body


def test_profiles_and_resume_versions_flow():
    seeker_token = register_user("seeker")
    employer_token = register_user("employer")

    seeker_headers = {"Authorization": f"Bearer {seeker_token}"}
    employer_headers = {"Authorization": f"Bearer {employer_token}"}

    seeker_profile = client.put(
        "/profiles/seeker",
        headers=seeker_headers,
        json={
            "full_name": "Alex Doe",
            "target_role": "Backend Developer",
            "location": "Remote",
            "about": "Python/FastAPI engineer",
            "skills": ["python", "fastapi", "postgresql"],
        },
    )
    assert seeker_profile.status_code == 200
    assert "python" in seeker_profile.json()["skills"]

    employer_profile = client.put(
        "/profiles/employer",
        headers=employer_headers,
        json={
            "company_name": "JobSkout LLC",
            "website": "https://jobskout.example",
            "description": "Hiring platform",
        },
    )
    assert employer_profile.status_code == 200
    assert employer_profile.json()["company_name"] == "JobSkout LLC"

    resume_version = client.post(
        "/resumes/versions",
        headers=seeker_headers,
        json={
            "name": "Backend CV v1",
            "target_role": "Python Backend Engineer",
            "content": {"experience": ["Company A"], "skills": ["python", "sql"]},
        },
    )
    assert resume_version.status_code == 201
    assert resume_version.json()["name"] == "Backend CV v1"

    versions = client.get("/resumes/versions", headers=seeker_headers)
    assert versions.status_code == 200
    assert len(versions.json()) >= 1


def test_sources_endpoint_returns_available_connectors():
    resp = client.get("/sources")
    assert resp.status_code == 200
    names = [item["name"] for item in resp.json()]
    assert "hh" in names
    assert "company_sites" in names
    assert "rss" in names


def test_employer_vacancy_ownership_crud():
    employer_a = register_user("employer")
    employer_b = register_user("employer")
    headers_a = {"Authorization": f"Bearer {employer_a}"}
    headers_b = {"Authorization": f"Bearer {employer_b}"}

    create = client.post(
        "/vacancies",
        headers=headers_a,
        json={
            "source": "manual",
            "external_id": f"manual-owned-{int(time.time())}",
            "title": "Backend Engineer",
            "company": "Owned Co",
            "location": "Remote",
            "employment_type": "full-time",
            "experience_level": "middle",
            "salary_from": 180000,
            "salary_to": 260000,
            "currency": "RUB",
            "description": "Python, FastAPI, PostgreSQL",
            "applications_count": 0,
        },
    )
    assert create.status_code == 201
    vacancy_id = create.json()["id"]

    mine = client.get("/vacancies/my", headers=headers_a)
    assert mine.status_code == 200
    mine_ids = [item["id"] for item in mine.json()]
    assert vacancy_id in mine_ids

    update = client.put(
        f"/vacancies/{vacancy_id}",
        headers=headers_a,
        json={"title": "Backend Engineer Updated", "applications_count": 3},
    )
    assert update.status_code == 200
    assert update.json()["title"] == "Backend Engineer Updated"

    archive = client.post(f"/vacancies/{vacancy_id}/archive", headers=headers_a)
    assert archive.status_code == 200
    assert archive.json()["status"] == "archived"

    mine_archived = client.get("/vacancies/my?status=archived", headers=headers_a)
    assert mine_archived.status_code == 200
    archived_owned_ids = [item["id"] for item in mine_archived.json()]
    assert vacancy_id in archived_owned_ids

    public_list = client.get("/vacancies")
    assert public_list.status_code == 200
    public_ids = [item["id"] for item in public_list.json()]
    assert vacancy_id not in public_ids

    archived_list = client.get("/vacancies?include_archived=true")
    assert archived_list.status_code == 200
    archived_ids = [item["id"] for item in archived_list.json()]
    assert vacancy_id in archived_ids

    publish = client.post(f"/vacancies/{vacancy_id}/publish", headers=headers_a)
    assert publish.status_code == 200
    assert publish.json()["status"] == "published"

    promote = client.post(f"/vacancies/{vacancy_id}/promote", headers=headers_a, json={"days": 3})
    assert promote.status_code == 200
    assert promote.json()["status"] == "promoted"

    analytics = client.get("/vacancies/my/analytics", headers=headers_a)
    assert analytics.status_code == 200
    assert analytics.json()["total"] >= 1

    actions = client.get("/vacancies/my/actions?limit=20", headers=headers_a)
    assert actions.status_code == 200
    action_names = [item["action"] for item in actions.json()]
    assert "vacancy_created" in action_names
    assert "vacancy_archived" in action_names
    assert "vacancy_published" in action_names
    assert "vacancy_promoted" in action_names

    archived_actions = client.get("/vacancies/my/actions?action=vacancy_archived&limit=20", headers=headers_a)
    assert archived_actions.status_code == 200
    for item in archived_actions.json():
        assert item["action"] == "vacancy_archived"

    paged = client.get("/vacancies/my/page?page=1&page_size=5", headers=headers_a)
    assert paged.status_code == 200
    assert "items" in paged.json()
    assert "total" in paged.json()

    exported = client.get("/vacancies/my/actions/export?limit=20", headers=headers_a)
    assert exported.status_code == 200
    assert "text/csv" in exported.headers.get("content-type", "")

    promo_location = f"PromoCity-{int(time.time())}"
    promo_first = client.post(
        "/vacancies",
        headers=headers_a,
        json={
            "source": "manual",
            "external_id": f"manual-promo-a-{int(time.time())}",
            "title": "Promoted Vacancy",
            "company": "Owned Co",
            "location": promo_location,
            "employment_type": "full-time",
            "experience_level": "middle",
            "salary_from": 180000,
            "salary_to": 260000,
            "currency": "RUB",
            "description": "Python remote",
            "applications_count": 0,
        },
    )
    assert promo_first.status_code == 201
    promo_first_id = promo_first.json()["id"]
    time.sleep(1)
    promo_second = client.post(
        "/vacancies",
        headers=headers_a,
        json={
            "source": "manual",
            "external_id": f"manual-promo-b-{int(time.time())}",
            "title": "Regular Vacancy",
            "company": "Owned Co",
            "location": promo_location,
            "employment_type": "full-time",
            "experience_level": "middle",
            "salary_from": 180000,
            "salary_to": 260000,
            "currency": "RUB",
            "description": "Python remote",
            "applications_count": 0,
        },
    )
    assert promo_second.status_code == 201
    promo_second_id = promo_second.json()["id"]
    promote_first = client.post(f"/vacancies/{promo_first_id}/promote", headers=headers_a, json={"days": 7})
    assert promote_first.status_code == 200
    listing = client.get(f"/vacancies?location={promo_location}")
    assert listing.status_code == 200
    listing_ids = [item["id"] for item in listing.json()]
    assert promo_first_id in listing_ids and promo_second_id in listing_ids
    assert listing_ids.index(promo_first_id) < listing_ids.index(promo_second_id)

    not_allowed = client.delete(f"/vacancies/{vacancy_id}", headers=headers_b)
    assert not_allowed.status_code == 404

    delete_ok = client.delete(f"/vacancies/{vacancy_id}", headers=headers_a)
    assert delete_ok.status_code == 200
    assert delete_ok.json()["status"] == "soft_deleted"

    deleted_actions = client.get("/vacancies/my/actions?action=vacancy_soft_deleted&limit=20", headers=headers_a)
    assert deleted_actions.status_code == 200
    assert any(item["vacancy_id"] == vacancy_id for item in deleted_actions.json())
