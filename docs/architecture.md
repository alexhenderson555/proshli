# JobSkout Architecture (MVP)

## Domains

- `Auth & Roles`: seeker/employer registration and access control.
- `Vacancy Aggregation`: normalized vacancies from multiple sources.
- `Resume`: upload + text extraction (PDF supported).
- `AI Assistant`: career-only assistant with strict guardrails and usage limits.
- `Digests`: daily/weekly delivery preferences for Telegram and email.

## Backend Design

- API: FastAPI (`backend/app/main.py`)
- DB: SQLAlchemy models in `backend/app/models.py`
- Security: JWT + password hashing (`backend/app/auth.py`)
- Guardrails: domain classifier + daily AI quota (`backend/app/services/ai_guardrails.py`)
- Ingestion pipeline: connectors + raw payload storage + dedupe (`backend/app/services/ingestion.py`)
- Digest ranking: resume skill matching + low-competition signal (`backend/app/services/digest.py`)

## Key Product Constraints (Implemented)

- AI only accepts career-related prompts.
- Every AI call is counted for daily per-user usage limiting.
- Digest preferences are configurable by user and persisted.
- Vacancy creation is restricted to `employer` role.
- Resume upload is restricted to `seeker` role.
- Ingestion runs are traceable (`ingest_runs`) and raw payloads are retained (`raw_vacancies`).

## Next Milestones

1. Replace demo connectors with legal production integrations (official APIs/feeds).
2. Add scheduler/worker for automatic ingestion and digest dispatch.
3. Build web frontend for:
   - role-based auth
   - vacancy discovery
   - resume constructor + upload
   - digest settings
4. Build Telegram bot for:
   - registration binding
   - instant search and digest setup
5. Expand CI quality gates:
   - linters
   - unit/integration/e2e tests
   - security checks
