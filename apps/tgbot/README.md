# Otklik.ai Telegram Bot (scaffold)

## Что делает

Telegram-бот Otklik.ai: онбординг, настройка периодичности дайджеста
(`daily` / `weekly`), привязка **Telegram chat ID** к аккаунту через
короткоживущий код из веба (см. поток `/link` в корневом `README`).

> **Статус:** scaffold. В Sprint 2 переедет на отдельный `pyproject.toml`
> + Dockerfile и будет деплоиться как сервис рядом с API/workers.

## Переменные окружения

| Переменная | Назначение |
|------------|------------|
| `TELEGRAM_BOT_TOKEN` | Токен от BotFather |
| `OTKLIK_API_URL` | URL API. По умолчанию `http://127.0.0.1:8000`. Старый `JOBSKOUT_API_URL` тоже принимается как fallback. |
| `BOT_SERVICE_KEY` | Shared secret с API для service-to-service auth |
| `REQUIRE_CHANNEL_SUBSCRIPTION` | `true`/`false` — гейт по подписке на канал |
| `REQUIRED_CHANNEL_USERNAME` | `@channel` для гейта |
| `EMPLOYER_PROMO_URL` | Ссылка на канал для работодателей |

## Запуск (dev)

```bash
cd apps/tgbot
python main.py
```

После Sprint 2 будет `uv run` через локальный `pyproject.toml`.

## Траблшутинг

| Проблема | Что проверить |
|----------|----------------|
| Нет ответа бота | Токен, сеть до `api.telegram.org`, прокси при необходимости. |
| API 401 | `BOT_SERVICE_KEY` совпадает с тем, что в API; user-JWT не протух. |
| Линк не срабатывает | Код из веба не истёк, `OTKLIK_API_URL` правильный, логи API. |
