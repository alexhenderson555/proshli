# JobSkout Telegram Bot (Scaffold)

This bot is a starter for:

- onboarding users from Telegram
- setting digest frequency (`daily` / `weekly`)
- connecting Telegram chat ID to digest preferences in API

## Run

1. Install deps (shared from backend):
   - `pip install -r ../backend/requirements.txt`
2. Set env vars:
   - `TELEGRAM_BOT_TOKEN`
   - `JOBSKOUT_API_URL` (default: `http://127.0.0.1:8000`)
   - `JOBSKOUT_USER_TOKEN` (JWT of user for API calls)
3. Run:
   - `python main.py`

## Notes

- Current scaffold uses one JWT token from env for simplicity.
- Next iteration should map each Telegram user to a JobSkout user account.
