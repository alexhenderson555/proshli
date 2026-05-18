"""Typed application settings backed by pydantic-settings.

All values are sourced from the process environment, falling back to a local
``.env`` file (see ``apps/api/.env.example``).  ``get_settings`` is cached so
that one ``Settings`` instance is reused across the process.

Note: many fields are carried over from the legacy ``BaseModel``-based settings
to preserve behaviour for callers in services/, connectors/, and the
not-yet-converted route handlers in ``main.py``.  As the migration progresses,
unused fields will be retired.
"""

from functools import lru_cache
from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Secrets we refuse to keep at their development defaults outside of dev/test.
# Adding a value here is the single point where you opt a new secret into the
# guard.
_SECRET_DEFAULTS: dict[str, str] = {
    "jwt_secret": "change-me-in-prod-please",
    "bot_service_key": "change-me-bot-service-key",
    # Wave 2: ЮKassa shop secret must be set for any non-dev environment that
    # exposes /billing/* routes. Empty string is the dev-friendly default —
    # the guard rejects it once app_env leaves dev/test.
    "yookassa_secret_key": "",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ------------------------------------------------------------------ app
    app_env: str = Field(default="development")
    app_log_level: str = Field(default="INFO")

    # ------------------------------------------------------------------ data
    database_url: str = Field(default="postgresql+asyncpg://proshli:proshli@localhost:5432/proshli")
    auto_create_schema: bool = Field(default=False)

    redis_url: str = Field(default="redis://localhost:6379/0")
    celery_broker_url: str = Field(default="redis://localhost:6379/1")
    celery_result_backend: str = Field(default="redis://localhost:6379/2")

    # ------------------------------------------------------------------ auth
    jwt_secret: str = Field(default="change-me-in-prod-please")
    jwt_algorithm: str = Field(default="HS256")
    # Single source of truth for the access-token TTL.  The previous duplicate
    # field ``jwt_access_token_ttl_minutes`` (60) silently lost to its sibling
    # ``access_token_expire_minutes`` (1440) — tokens lived 24× longer than the
    # documented TTL.  Wave 6 fixes that.  Sessions extend transparently via
    # the refresh-token flow introduced in Wave 7.
    access_token_expire_minutes: int = Field(default=60)
    refresh_token_expire_minutes: int = Field(default=60 * 24 * 14)  # 14 days

    # ------------------------------------------------------------------ bot
    bot_service_key: str = Field(default="change-me-bot-service-key")
    telegram_bot_token: str = Field(default="")
    telegram_link_code_ttl_minutes: int = Field(default=15)
    # Wave: TG publication targets. ``telegram_publication_group_id`` is the
    # forum supergroup chat id (negative integer in string form, e.g.
    # ``"-1001234567890"``) into which the prefilter+publisher pair posts. Empty
    # string disables publication (dev / CI default) — the publisher task logs
    # ``publisher.disabled`` and exits cleanly when this is unset, so beat can
    # still tick without errors. ``telegram_publication_channel_id`` is reserved
    # for Phase 2 (manual approval → channel @proshli).
    telegram_publication_group_id: str = Field(default="")
    telegram_publication_channel_id: str = Field(default="")
    # Max rows the publisher drains per 15-min beat tick. TG caps at 20
    # messages/min per group; 80 ÷ 15 min keeps us safely under that with
    # headroom for retries.
    telegram_publication_batch_size: int = Field(default=80)
    # Hard cap on enqueue attempts before a row is marked ``failed`` for
    # operator inspection. Matches the spec's "max 3 attempts" rule.
    telegram_publication_max_attempts: int = Field(default=3)
    # Phase 2 channel approval — admin Telegram chat id (private DM) that
    # receives the daily top-8 with inline ✅/❌ buttons. Empty disables
    # the approval flow (the scoring task logs ``channel_approval.disabled``
    # and exits cleanly).
    telegram_admin_chat_id: str = Field(default="")
    # Daily top-N candidates surfaced to the admin DM. 8 fits comfortably
    # in one TG message even if every card spans a few lines.
    channel_approval_top_n: int = Field(default=8)

    # ------------------------------------------------------------------ ai
    ai_daily_request_limit: int = Field(default=25)
    ai_max_input_chars: int = Field(default=1000)
    # Anthropic Claude — wave 3 replaces the rule-based extractor with the
    # real model. Empty key keeps dev startup happy; the LLM service short
    # circuits to the legacy extractor when unset.
    anthropic_api_key: str = Field(default="")
    anthropic_model: str = Field(default="claude-sonnet-4-5-20250929")
    anthropic_max_tokens: int = Field(default=1024)

    # Wave 4: Voyage AI for vacancy/query embeddings (semantic search).
    # Empty key → :class:`RuleBasedEmbeddingService` fallback, same pattern
    # as the LLM service. ``voyage-3`` is 1024-d and the column type in
    # migration 0012 must match.
    voyage_api_key: str = Field(default="")
    voyage_model: str = Field(default="voyage-3")

    # ------------------------------------------------------------------ billing (ЮKassa)
    # Wave 2 wires ЮKassa billing for the free / pro / employer tiers
    # (РФ-focused product). Recurring billing is implemented via
    # ``save_payment_method`` → autopayments — the first checkout asks the
    # user to authorise card-on-file, subsequent renewals use the saved
    # ``payment_method_id``.
    yookassa_shop_id: str = Field(default="")
    yookassa_secret_key: str = Field(default="")
    # Used to build return_url for checkout and to craft Telegram deep-links
    # from server-side notifications.
    app_base_url: str = Field(default="http://localhost:3000")

    # ------------------------------------------------------------------ ingestion sources
    rss_source_urls: str = Field(default="")
    hh_base_url: str = Field(default="https://api.hh.ru")
    hh_search_text: str = Field(default="python developer")
    hh_region: str = Field(default="113")  # 113 = Russia
    hh_per_page: int = Field(default=100)
    hh_live_enabled: bool = Field(default=True)
    hh_live_limit: int = Field(default=2000)
    # Comma-separated list of HH search queries; empty → use the default
    # 47-role roster from ``connectors.hh``.
    hh_search_queries: str = Field(default="")
    # Comma-separated HH area ids (113 = Russia). Empty → default sweep.
    hh_areas: str = Field(default="")
    # Hard cap on pages per (query, area) combination. HH allows up to 20
    # pages of 100 — 3 is plenty for "recent" sweeps every 10 min.
    hh_max_pages_per_query: int = Field(default=3)

    # ------------------------------------------------------------------ telegram scraping
    # User-account credentials (NOT the bot token). Get them from
    # https://my.telegram.org/apps. Empty values disable the Telethon path.
    telegram_api_id: str = Field(default="")
    telegram_api_hash: str = Field(default="")
    # Path (without .session suffix) where Telethon caches the auth session.
    # The worker container mounts /data as a volume so the session survives
    # restarts. The first run requires an interactive login via
    # ``python -m scripts.tg_login`` to create the file.
    telegram_session_path: str = Field(default="/data/proshli-tg")
    # Override the channel roster (comma-separated bare @handles). Empty →
    # use the default 79-channel curated list in connectors.telegram_channels.
    tg_channels: str = Field(default="")

    # ------------------------------------------------------------------ smtp
    smtp_host: str = Field(default="")
    smtp_port: int = Field(default=587)
    smtp_user: str = Field(default="")
    smtp_password: str = Field(default="")
    smtp_from_email: str = Field(default="noreply@proshli.local")

    # ------------------------------------------------------------------ observability
    sentry_dsn: str | None = Field(default=None)
    sentry_traces_sample_rate: float = Field(default=0.1)

    # ------------------------------------------------------------------ cors
    cors_allowed_origins: str = Field(default="http://localhost:3000,http://127.0.0.1:3000")

    # ------------------------------------------------------------------ proxies
    # Comma-separated list of CIDR ranges (or bare IPs) that we trust to set
    # ``X-Forwarded-For``. Empty default means: do NOT trust XFF, fall back to
    # ``request.client.host``. This is the safe posture for any host directly
    # reachable from the internet — otherwise anybody can spoof their source
    # IP by sending ``X-Forwarded-For: 185.71.76.0`` and walk past the ЮKassa
    # IP allow-list. Set to your reverse-proxy/CDN CIDR(s) in production
    # (e.g. ``10.0.0.0/8`` for an internal LB, or the Fly.io edge ranges).
    trusted_proxies: str = Field(default="")

    @property
    def trusted_proxies_list(self) -> list[str]:
        return [p.strip() for p in self.trusted_proxies.split(",") if p.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        """Parsed list form of CORS_ALLOWED_ORIGINS."""
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def cors_allow_origins(self) -> list[str]:
        """Legacy alias kept for callers in ``main.py``."""
        return self.cors_origins_list

    @property
    def rss_source_urls_list(self) -> list[str]:
        return [u.strip() for u in self.rss_source_urls.split(",") if u.strip()]

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        """Fail-fast in staging/production if a secret is still at its dev default.

        Mirrors the pattern from the tiangolo full-stack template
        (``_enforce_non_default_secrets``). Local ``development`` and ``test``
        runs are unaffected so contributors don't need to invent secrets.
        """
        if self.app_env in {"development", "test"}:
            return self
        offenders = [
            name
            for name, default in _SECRET_DEFAULTS.items()
            if getattr(self, name, None) == default
        ]
        if offenders:
            joined = ", ".join(offenders)
            raise ValueError(
                f"Refusing to start with default secret(s) in {self.app_env}: {joined}. "
                "Set proper values in the environment."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
