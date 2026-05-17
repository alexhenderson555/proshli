# Legacy sync scripts

These three scripts were written against the original sync SQLAlchemy
session (`app.database.SessionLocal`) and are currently broken — they reference
`SessionLocal` which was removed during the Sprint 1 async migration.

They are quarantined here pending Task 7 (workers), which will replace them
with proper Celery tasks living in `apps/workers/`.

Do not import from here.
