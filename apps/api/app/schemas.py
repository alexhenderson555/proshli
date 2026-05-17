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
