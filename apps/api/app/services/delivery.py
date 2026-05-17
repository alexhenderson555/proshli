import smtplib
from email.message import EmailMessage

import httpx
from app.config import settings


def _format_digest_text(items: list[dict[str, str]]) -> str:
    if not items:
        return "Сегодня релевантных вакансий не найдено."
    lines = []
    for idx, item in enumerate(items, start=1):
        lines.append(
            f"{idx}. {item['title']} @ {item['company']} ({item['location']})\n"
            f"   Почему: {item['score_reason']}"
        )
    return "\n\n".join(lines)


def send_telegram_digest(chat_id: str, items: list[dict[str, str]]) -> tuple[bool, str | None]:
    if not chat_id:
        return False, "Missing telegram chat id"
    if not settings.telegram_bot_token:
        # Dry-run mode for local/dev.
        return True, None

    text = _format_digest_text(items)
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text[:3900]}
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=payload)
        if response.status_code >= 400:
            return False, f"Telegram HTTP {response.status_code}"
        return True, None
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def send_email_digest(to_email: str, items: list[dict[str, str]]) -> tuple[bool, str | None]:
    if not to_email:
        return False, "Missing recipient email"
    if not settings.smtp_host or not settings.smtp_user or not settings.smtp_password:
        # Dry-run mode for local/dev.
        return True, None

    msg = EmailMessage()
    msg["Subject"] = "Otklik.ai: персональная подборка вакансий"
    msg["From"] = settings.smtp_from_email
    msg["To"] = to_email
    msg.set_content(_format_digest_text(items))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        return True, None
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
