from datetime import UTC, datetime


def now_utc() -> datetime:
    # Store naive UTC datetime for DB compatibility, but avoid utcnow() deprecation.
    return datetime.now(UTC).replace(tzinfo=None)
