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
    database_url: str = Field(
        default="postgresql+asyncpg://otklik:otklik@localhost:5432/otklik"
    )
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

    # ------------------------------------------------------------------ ai
    ai_daily_request_limit: int = Field(default=25)
    ai_max_input_chars: int = Field(default=1000)
    # Anthropic Claude — wave 3 replaces the rule-based extractor with the
    # real model. Empty key keeps dev startup happy; the LLM service short
    # circuits to the legacy extractor when unset.
    anthropic_api_key: str = Field(default="")
    anthropic_model: str = Field(default="claude-sonnet-4-5-20250929")
    anthropic_max_tokens: int = Field(default=1024)

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
    hh_per_page: int = Field(default=20)
    hh_live_enabled: bool = Field(default=True)
    hh_live_limit: int = Field(default=30)

    # ------------------------------------------------------------------ smtp
    smtp_host: str = Field(default="")
    smtp_port: int = Field(default=587)
    smtp_user: str = Field(default="")
    smtp_password: str = Field(default="")
    smtp_from_email: str = Field(default="noreply@otklik.local")

    # ------------------------------------------------------------------ observability
    sentry_dsn: str | None = Field(default=None)
    sentry_traces_sample_rate: float = Field(default=0.1)

    # ------------------------------------------------------------------ cors
    cors_allowed_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000"
    )

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
