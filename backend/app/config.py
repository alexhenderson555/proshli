import os

from pydantic import BaseModel


class Settings(BaseModel):
    jwt_secret: str = os.getenv("JWT_SECRET", "change-me-in-prod")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./jobskout.db")
    auto_create_schema: bool = os.getenv("AUTO_CREATE_SCHEMA", "true").lower() == "true"
    ai_daily_request_limit: int = int(os.getenv("AI_DAILY_REQUEST_LIMIT", "25"))
    ai_max_input_chars: int = int(os.getenv("AI_MAX_INPUT_CHARS", "1000"))
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    bot_service_key: str = os.getenv("BOT_SERVICE_KEY", "change-me-bot-service-key")
    telegram_link_code_ttl_minutes: int = int(os.getenv("TELEGRAM_LINK_CODE_TTL_MINUTES", "15"))
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from_email: str = os.getenv("SMTP_FROM_EMAIL", "noreply@jobskout.local")
    rss_source_urls: list[str] = [
        url.strip() for url in os.getenv("RSS_SOURCE_URLS", "").split(",") if url.strip()
    ]
    hh_base_url: str = os.getenv("HH_BASE_URL", "https://api.hh.ru")
    hh_search_text: str = os.getenv("HH_SEARCH_TEXT", "python developer")
    hh_region: str = os.getenv("HH_REGION", "113")  # 113 = Russia
    hh_per_page: int = int(os.getenv("HH_PER_PAGE", "20"))
    hh_live_enabled: bool = os.getenv("HH_LIVE_ENABLED", "true").lower() == "true"
    hh_live_limit: int = int(os.getenv("HH_LIVE_LIMIT", "30"))
    cors_allow_origins: list[str] = [
        item.strip()
        for item in os.getenv(
            "CORS_ALLOW_ORIGINS",
            "http://127.0.0.1:3000,http://localhost:3000,http://127.0.0.1:5500,http://localhost:5500",
        ).split(",")
        if item.strip()
    ]


settings = Settings()
