"""Interactive Telethon login — run once per VPS to provision the session.

Usage (inside the api container)::

    docker compose -f docker-compose.prod.yml exec api \
        uv run python -m scripts.tg_login

The script reads ``TELEGRAM_API_ID`` / ``TELEGRAM_API_HASH`` /
``TELEGRAM_PHONE`` from the environment, prompts for the SMS / Telegram-app
code interactively, and writes a ``.session`` file to
``TELEGRAM_SESSION_PATH`` (default ``/data/proshli-tg``). After that, the
``TelegramChannelsConnector`` can reuse it non-interactively on every Celery
beat tick.

Re-run only if the session expires (rare) or the phone number changes.
"""

from __future__ import annotations

import asyncio
import os
import sys


async def _main() -> int:
    try:
        from telethon import TelegramClient  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001
        print(f"telethon not installed: {exc}", file=sys.stderr)
        return 1

    api_id_raw = os.getenv("TELEGRAM_API_ID", "").strip()
    api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()
    phone = os.getenv("TELEGRAM_PHONE", "").strip()
    session_path = os.getenv("TELEGRAM_SESSION_PATH", "/data/proshli-tg")

    if not api_id_raw or not api_hash:
        print("TELEGRAM_API_ID and TELEGRAM_API_HASH must be set.", file=sys.stderr)
        return 2
    try:
        api_id = int(api_id_raw)
    except ValueError:
        print("TELEGRAM_API_ID must be an integer.", file=sys.stderr)
        return 2

    client = TelegramClient(session_path, api_id, api_hash)
    await client.connect()
    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"Already authorized as {getattr(me, 'username', None) or me.id}.")
        await client.disconnect()
        return 0

    if not phone:
        phone = input("Phone (international, e.g. +79001234567): ").strip()
    await client.send_code_request(phone)
    code = input("Code (from Telegram): ").strip()
    try:
        await client.sign_in(phone=phone, code=code)
    except Exception as exc:  # noqa: BLE001
        # 2FA password path.
        if "password" in str(exc).lower():
            password = input("Cloud password (2FA): ").strip()
            await client.sign_in(password=password)
        else:
            print(f"sign_in failed: {exc}", file=sys.stderr)
            await client.disconnect()
            return 3

    me = await client.get_me()
    print(f"Authorized as {getattr(me, 'username', None) or me.id}. Session saved at {session_path}.session")
    await client.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
