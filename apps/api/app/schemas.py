from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

RoleType = Literal["seeker", "employer"]
DigestFrequency = Literal["daily", "weekly"]


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: RoleType


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TelegramLinkCodeOut(BaseModel):
    code: str
    expires_at: datetime


class TelegramLinkConsumeRequest(BaseModel):
    code: str = Field(min_length=4, max_length=32)
    telegram_user_id: str = Field(min_length=1, max_length=64)
    telegram_chat_id: str = Field(min_length=1, max_length=64)
    telegram_username: str | None = None


class TelegramBotLoginRequest(BaseModel):
    telegram_user_id: str = Field(min_length=1, max_length=64)
    telegram_chat_id: str = Field(min_length=1, max_length=64)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    role: RoleType
    created_at: datetime

    model_config = {"from_attributes": True}


class VacancyOut(BaseModel):
    id: int
    source: str
    title: str
    company: str
    location: str
    employment_type: str
    experience_level: str
    salary_from: int | None
    salary_to: int | None
    currency: str
    description: str
    published_at: datetime
    applications_count: int
    is_active: bool
    archived_at: datetime | None
    is_deleted: bool
    deleted_at: datetime | None
    is_promoted: bool
    promotion_expires_at: datetime | None
    external_url: str | None = None
    match_score: float | None = None
    match_tier: Literal["strong", "decent", "stretch", "longshot"] | None = None
    # Match-score 2.0 — LLM-generated 1-2 sentence justification for why
    # this vacancy fits the caller's resume. Populated only by the
    # ``GET /vacancies/match-feed`` endpoint (or when a cached row exists
    # in ``match_reasonings``); ``None`` elsewhere keeps the contract
    # backwards-compatible for /vacancies, the digest, and employer views.
    match_reasoning: str | None = None
    # Reranker confidence in [0, 1]. Distinct from ``match_score`` (cosine
    # in [-1, 1]) so the FE can show both, or pick the rerank score as the
    # primary signal in the "For me" tab without losing the cosine fallback.
    rerank_score: float | None = None

    model_config = {"from_attributes": True}


class VacancyCreateRequest(BaseModel):
    source: str
    external_id: str
    title: str
    company: str
    location: str
    employment_type: str = "full-time"
    experience_level: str = "middle"
    salary_from: int | None = None
    salary_to: int | None = None
    currency: str = "RUB"
    description: str = ""
    applications_count: int = 0


class VacancyUpdateRequest(BaseModel):
    title: str | None = None
    company: str | None = None
    location: str | None = None
    employment_type: str | None = None
    experience_level: str | None = None
    salary_from: int | None = None
    salary_to: int | None = None
    currency: str | None = None
    description: str | None = None
    applications_count: int | None = None


class VacancyPromoteRequest(BaseModel):
    days: int = Field(default=7, ge=1, le=30)


class ResumeOut(BaseModel):
    id: int
    name: str
    parsed_skills: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DigestPreferenceUpdate(BaseModel):
    frequency: DigestFrequency = "daily"
    via_telegram: bool = True
    via_email: bool = False
    telegram_chat_id: str | None = None


class DigestPreferenceOut(BaseModel):
    frequency: DigestFrequency
    via_telegram: bool
    via_email: bool
    telegram_chat_id: str | None
    updated_at: datetime

    model_config = {"from_attributes": True}


class AiChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class AiChatResponse(BaseModel):
    accepted: bool
    message: str
    extracted_filters: dict[str, str] | None = None


class IngestRunOut(BaseModel):
    id: int
    source: str
    fetched_count: int
    inserted_count: int
    deduped_count: int
    started_at: datetime
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class DigestItem(BaseModel):
    vacancy_id: int
    title: str
    company: str
    location: str
    score_reason: str


class DigestPreviewOut(BaseModel):
    frequency: DigestFrequency
    channels: list[str]
    items: list[DigestItem]


class SchedulerRunOut(BaseModel):
    ingestion_runs: int
    ingestion_inserted: int
    ingestion_deduped: int
    digests_sent: int
    digests_skipped: int
    digests_failed: int


class SourceConnectorOut(BaseModel):
    name: str


class EmployerVacancyAnalyticsOut(BaseModel):
    total: int
    active: int
    archived: int


class EmployerActionLogOut(BaseModel):
    id: int
    vacancy_id: int | None
    action: str
    meta: dict[str, object]
    created_at: datetime


class EmployerVacancyPageOut(BaseModel):
    items: list[VacancyOut]
    total: int
    page: int
    page_size: int


class SeekerProfileUpdate(BaseModel):
    full_name: str = ""
    target_role: str = ""
    location: str = ""
    about: str = ""
    skills: list[str] = []


class SeekerProfileOut(BaseModel):
    full_name: str
    target_role: str
    location: str
    about: str
    skills: list[str]
    updated_at: datetime


class EmployerProfileUpdate(BaseModel):
    company_name: str = ""
    website: str = ""
    description: str = ""


class EmployerProfileOut(BaseModel):
    company_name: str
    website: str
    description: str
    verified: bool
    updated_at: datetime


class ResumeVersionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    target_role: str = ""
    content: dict[str, object]


class ResumeVersionOut(BaseModel):
    id: int
    name: str
    target_role: str
    content: dict[str, object]
    created_at: datetime


class ResumeImproveRequest(BaseModel):
    """Optional hint payload for ``POST /resumes/versions/{id}/improve``.

    Both fields are optional — the endpoint defaults to the version's own
    ``target_role`` if ``target_role`` is empty, and skips the per-turn
    focus block if ``focus`` is empty.
    """

    target_role: str = Field(default="", max_length=128)
    focus: str = Field(default="", max_length=500)


class ResumeImproveResponse(BaseModel):
    """LLM-improved resume summary + concrete suggestions.

    ``summary`` is a 1–2 sentence pitch the seeker can paste at the top of
    a resume / cover letter. ``suggestions`` is a short bulleted list of
    actionable rewrites (each item ≤ 1 sentence). ``used_today`` / ``limit``
    mirror the AI-budget surface so the bot can warn the user when they're
    close to the cap. ``backend`` is ``"anthropic"`` or ``"rule_based"`` so
    the FE / bot can distinguish a real LLM call from the offline fallback.
    """

    summary: str
    suggestions: list[str]
    used_today: int
    limit: int
    backend: str


CoverLetterTone = Literal["formal", "friendly"]
CoverLetterLanguage = Literal["ru", "en"]


class CoverLetterRequest(BaseModel):
    """Generate-cover-letter input.

    Seeker passes the vacancy id and picks tone + language. We resolve
    the seeker's profile + latest resume server-side — the FE doesn't
    have to assemble a payload from disparate sources.
    """

    vacancy_id: int
    tone: CoverLetterTone = "formal"
    language: CoverLetterLanguage = "ru"


class CoverLetterResponse(BaseModel):
    """AI cover-letter draft + the standard budget envelope.

    ``body`` is the letter text (3 short paragraphs, plain prose, no
    salutation/sign-off — those live in the FE so the seeker can
    customise the addressee without re-spending budget).
    """

    body: str
    used_today: int
    limit: int
    backend: str


# --------------------------------------------------------------------- billing


class PlanOut(BaseModel):
    """Public plan info — exposed via ``GET /billing/plans``."""

    slug: str
    name_ru: str
    price_rub: int
    ai_daily_limit: int
    semantic_search: bool
    digest_frequency: str

    model_config = {"from_attributes": True}


class SubscriptionOut(BaseModel):
    """Current subscription state of the authenticated user."""

    plan: PlanOut
    status: str
    current_period_end: datetime | None
    cancel_at_period_end: bool = False

    model_config = {"from_attributes": True}


class CheckoutRequest(BaseModel):
    """Body for ``POST /billing/checkout`` — pick the target plan by slug."""

    plan_slug: str = Field(min_length=1, max_length=32)
    return_url: str | None = Field(default=None, max_length=512)


class CheckoutResponse(BaseModel):
    confirmation_url: str
    payment_id: str
    status: str


class MatchScoreOut(BaseModel):
    score: float
    tier: Literal["strong", "decent", "stretch", "longshot"]
    # Match-score 2.0 — cached LLM reasoning if a ``match_reasonings`` row
    # exists for the (resume, vacancy) pair. ``None`` when no rerank has
    # been computed yet, or when the row aged out of the TTL. The detail
    # page renders this as a "Why this fits?" blurb under the pill.
    reasoning: str | None = None
    rerank_score: float | None = None


class VacancyStatsOut(BaseModel):
    """Public, anonymous-readable counts for the landing-page hero strip.

    Exposes only aggregate, non-PII numbers — the landing copy promises
    "не HH-спам, а сигнал" and these values back that up with live data
    instead of the previous hard-coded `40+ / 10× / 24/7` placeholders.
    """

    total: int
    last_24h: int
    sources: int


# --------------------------------------------------------------------- kanban

ApplicationStatus = Literal["saved", "applied", "interview", "offer", "rejected"]


class ApplicationCreateRequest(BaseModel):
    """Body for ``POST /applications`` — seekers track a vacancy in their pipeline.

    ``status`` defaults to ``saved`` (the leftmost kanban lane). Sending an
    explicit status is supported so the FE "Apply" button can skip the
    save-then-promote round-trip.
    """

    vacancy_id: int
    status: ApplicationStatus = "saved"
    notes: str = Field(default="", max_length=4000)


class ApplicationUpdateRequest(BaseModel):
    """Body for ``PATCH /applications/{id}`` — move between lanes or edit notes."""

    status: ApplicationStatus | None = None
    notes: str | None = Field(default=None, max_length=4000)


class ApplicationOut(BaseModel):
    id: int
    vacancy_id: int
    status: ApplicationStatus
    notes: str
    created_at: datetime
    updated_at: datetime
    vacancy: VacancyOut

    model_config = {"from_attributes": True}


class ApplicationCountsOut(BaseModel):
    """One number per kanban lane, used by the dashboard overview tab."""

    saved: int
    applied: int
    interview: int
    offer: int
    rejected: int
