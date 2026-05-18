from datetime import datetime

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.time_utils import now_utc

# Mirrors ``app.services.embeddings.EMBEDDING_DIM``. Inlined here to avoid a
# circular import (models is loaded before services in alembic's env.py).
_EMBEDDING_DIM = 1024


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), index=True)  # seeker | employer
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)

    resumes: Mapped[list["Resume"]] = relationship(back_populates="owner")
    digest_preference: Mapped["DigestPreference"] = relationship(
        back_populates="owner", uselist=False
    )
    ai_usage_events: Mapped[list["AiUsageEvent"]] = relationship(back_populates="owner")
    seeker_profile: Mapped["SeekerProfile"] = relationship(back_populates="owner", uselist=False)
    employer_profile: Mapped["EmployerProfile"] = relationship(back_populates="owner", uselist=False)
    resume_versions: Mapped[list["ResumeVersion"]] = relationship(back_populates="owner")
    employer_vacancies: Mapped[list["EmployerVacancy"]] = relationship(back_populates="owner")
    employer_actions: Mapped[list["EmployerActionLog"]] = relationship(back_populates="owner")
    subscription: Mapped["Subscription | None"] = relationship(
        back_populates="owner", uselist=False
    )


class Plan(Base):
    """Billing tier definition.

    Wave 2 seeds three rows via the alembic migration:

    * ``free``     — 0 ₽ / mo, AI 5/day, no semantic search
    * ``pro``      — 490 ₽ / mo, AI 50/day, semantic search on, daily digest
    * ``employer`` — 2490 ₽ / mo, AI 100/day, semantic search on, daily digest

    The row is intentionally lightweight: pricing + feature flags only. Per-user
    state (renewal time, payment-method handle) lives on ``Subscription``.
    """

    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    slug: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name_ru: Mapped[str] = mapped_column(String(120))
    price_rub: Mapped[int] = mapped_column(Integer, default=0)
    ai_daily_limit: Mapped[int] = mapped_column(Integer, default=5)
    semantic_search: Mapped[bool] = mapped_column(Boolean, default=False)
    digest_frequency: Mapped[str] = mapped_column(String(20), default="weekly")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class Subscription(Base):
    """A user's current billing state.

    1-to-1 with ``User``. ``yookassa_payment_method_id`` holds the saved
    payment-method handle from the initial checkout (``save_payment_method=True``);
    the hourly Celery beat task uses it to charge recurring renewals without
    user interaction.

    ``status`` transitions:

    * ``pending``   — checkout created, awaiting ``payment.succeeded`` webhook
    * ``active``    — paid, ``current_period_end`` in the future
    * ``past_due``  — renewal charge failed, grace period before downgrade
    * ``canceled``  — user opted out; access keeps until ``current_period_end``
    """

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), unique=True, index=True
    )
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), index=True)
    yookassa_payment_method_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
    )
    last_payment_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, index=True
    )

    owner: Mapped[User] = relationship(back_populates="subscription")
    plan: Mapped[Plan] = relationship()


class Vacancy(Base):
    __tablename__ = "vacancies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(64), index=True)
    external_id: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    company: Mapped[str] = mapped_column(String(255), index=True)
    location: Mapped[str] = mapped_column(String(128), index=True)
    employment_type: Mapped[str] = mapped_column(String(64), default="full-time")
    experience_level: Mapped[str] = mapped_column(String(64), default="middle")
    salary_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_to: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="RUB")
    description: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, index=True)
    applications_count: Mapped[int] = mapped_column(Integer, default=0, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_promoted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    promotion_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Wave 4: semantic search. Nullable because old rows haven't been
    # backfilled yet and the rule-based fallback intentionally leaves
    # vectors blank (no semantic value). Indexed via IVFFLAT cosine ops
    # in migration 0012; the index is declared at DDL level rather than
    # via ORM hints so the build parameters (``lists = 100``) stay in
    # one place.
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(_EMBEDDING_DIM), nullable=True
    )
    # Phase 1 TG-publication routing — see migration 0014. ``topic_id`` is
    # one of 1..28 (see ``app.services.tg_topics.TOPICS``); ``classified_at``
    # is the timestamp of the last classifier run so re-classification can
    # be triggered by age, not just nullability.
    topic_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    classified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    employer_links: Mapped[list["EmployerVacancy"]] = relationship(back_populates="vacancy")


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    raw_text: Mapped[str] = mapped_column(Text)
    parsed_skills: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)

    owner: Mapped[User] = relationship(back_populates="resumes")


class DigestPreference(Base):
    __tablename__ = "digest_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    frequency: Mapped[str] = mapped_column(String(20), default="daily")  # daily | weekly
    via_telegram: Mapped[bool] = mapped_column(Boolean, default=True)
    via_email: Mapped[bool] = mapped_column(Boolean, default=False)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)

    owner: Mapped[User] = relationship(back_populates="digest_preference")


class AiUsageEvent(Base):
    __tablename__ = "ai_usage_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    prompt_chars: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, index=True)

    owner: Mapped[User] = relationship(back_populates="ai_usage_events")


class RawVacancy(Base):
    __tablename__ = "raw_vacancies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(64), index=True)
    external_id: Mapped[str] = mapped_column(String(128), index=True)
    payload_json: Mapped[str] = mapped_column(Text)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, index=True)


class IngestRun(Base):
    __tablename__ = "ingest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(64), index=True)
    fetched_count: Mapped[int] = mapped_column(Integer, default=0)
    inserted_count: Mapped[int] = mapped_column(Integer, default=0)
    deduped_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DigestDispatchEvent(Base):
    __tablename__ = "digest_dispatch_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    frequency: Mapped[str] = mapped_column(String(20), index=True)  # daily | weekly
    channels_csv: Mapped[str] = mapped_column(String(120), default="")
    items_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="sent")  # sent | skipped | failed
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, index=True)


class SeekerProfile(Base):
    __tablename__ = "seeker_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    target_role: Mapped[str] = mapped_column(String(128), default="")
    location: Mapped[str] = mapped_column(String(128), default="")
    about: Mapped[str] = mapped_column(Text, default="")
    skills_csv: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)

    owner: Mapped[User] = relationship(back_populates="seeker_profile")


class EmployerProfile(Base):
    __tablename__ = "employer_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    company_name: Mapped[str] = mapped_column(String(255), default="")
    website: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)

    owner: Mapped[User] = relationship(back_populates="employer_profile")


class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    target_role: Mapped[str] = mapped_column(String(128), default="")
    content_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)

    owner: Mapped[User] = relationship(back_populates="resume_versions")


class EmployerVacancy(Base):
    __tablename__ = "employer_vacancies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)

    owner: Mapped[User] = relationship(back_populates="employer_vacancies")
    vacancy: Mapped[Vacancy] = relationship(back_populates="employer_links")


class EmployerActionLog(Base):
    __tablename__ = "employer_action_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    vacancy_id: Mapped[int | None] = mapped_column(ForeignKey("vacancies.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    meta_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, index=True)

    owner: Mapped[User] = relationship(back_populates="employer_actions")


class TelegramLinkCode(Base):
    __tablename__ = "telegram_link_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, index=True)


class ProcessedWebhookEvent(Base):
    """Replay-protection for external webhooks.

    A row exists per ``(source, event_id)`` we've already processed. Webhook
    handlers must ``INSERT`` here *before* touching billing state — the
    unique-index violation on the second delivery short-circuits the rest
    of the handler so re-deliveries from the provider (network blips,
    retries, replay attacks) can't extend a subscription twice or grant
    two refunds for the same payment.

    Why ``object_id`` is captured too:

    * For ЮKassa, ``event.object.id`` is the payment / refund identifier.
      Logging it next to the event id makes audits cheap when investigating
      a customer dispute.

    The table is append-only — old rows can be pruned by ops at any time
    (the uniqueness window only matters for the provider's retry horizon,
    typically ≤24h), but pruning is intentionally not automated here so
    a misconfigured cron can't accidentally enable replays.
    """

    __tablename__ = "processed_webhook_events"
    # Atomicity hinge — see the class docstring. The webhook handler
    # INSERTs first; a duplicate ``(source, event_id)`` pair raises
    # ``IntegrityError`` and short-circuits with ``{"replay": True}``.
    # Migration 0013 creates the matching index against a live DB;
    # this constraint mirrors it for ``Base.metadata.create_all`` in
    # the test fixture (without it the tests get a table that allows
    # replays through, breaking ``test_webhook_replay_does_not_extend_period``).
    __table_args__ = (
        UniqueConstraint(
            "source", "event_id", name="uq_processed_webhook_events_source_event"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(32), index=True)
    event_id: Mapped[str] = mapped_column(String(128), index=True)
    event_type: Mapped[str] = mapped_column(String(64))
    object_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, index=True)


class TelegramAccountLink(Base):
    __tablename__ = "telegram_account_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    telegram_user_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    telegram_chat_id: Mapped[str] = mapped_column(String(64), index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, index=True)


class PublicationQueueItem(Base):
    """One vacancy → one TG-surface post.

    Phase 1 plumbing for the TG publication subsystem (see
    ``docs/superpowers/specs/2026-05-18-tg-publication-design.md``). The
    publisher worker reads rows where ``status == 'pending'`` and
    ``scheduled_for <= now``, ordered by ``scheduled_for`` ASC.

    The unique constraint on ``(vacancy_id, target)`` is the dedup hinge —
    a vacancy can have at most one row per target surface
    (``'group'`` or ``'channel'``). Re-enqueue is a deliberate admin
    action (delete + insert), not a race-condition outcome.
    """

    __tablename__ = "publication_queue"
    __table_args__ = (
        UniqueConstraint(
            "vacancy_id",
            "target",
            name="uq_publication_queue_vacancy_target",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    vacancy_id: Mapped[int] = mapped_column(
        ForeignKey("vacancies.id", ondelete="CASCADE"), index=True
    )
    # 'group' (28-topic forum supergroup) | 'channel' (curated facade).
    target: Mapped[str] = mapped_column(String(16), index=True)
    # 1..28 for ``target='group'``; NULL for ``target='channel'`` since
    # the channel has no topic structure.
    topic_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    rendered_text: Mapped[str] = mapped_column(Text)
    # pending | published | failed | dismissed
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime, default=now_utc, index=True
    )
    published_message_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
