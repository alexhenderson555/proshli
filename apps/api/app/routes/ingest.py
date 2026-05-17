"""Ingestion + connector discovery endpoints.

Triggering a fetch is employer-gated because it's an external-network call —
once we move ingestion onto Celery beat (Task 7), this endpoint shrinks to
an "enqueue task" wrapper.  ``GET /sources`` stays anonymous so the FE can
populate a filter dropdown without auth.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.connectors.registry import connector_map
from app.deps import DbSession
from app.models import User
from app.schemas import IngestRunOut, SourceConnectorOut
from app.services.ingestion import run_ingestion

router = APIRouter(tags=["ingest"])


@router.post("/ingest/{source_name}", response_model=IngestRunOut)
async def ingest_source(
    source_name: str,
    db: DbSession,
    current_user: User = Depends(get_current_user),
) -> IngestRunOut:
    if current_user.role != "employer":
        raise HTTPException(
            status_code=403, detail="Only employers can run source ingestion"
        )

    connector = connector_map().get(source_name)
    if not connector:
        raise HTTPException(status_code=404, detail="Unknown source")

    payloads = connector.fetch()
    run = await run_ingestion(db, source_name=source_name, payloads=payloads)
    # FastAPI/pydantic will adapt the ORM instance via ``from_attributes`` on
    # the response model, but mypy sees ``run_ingestion``'s declared return
    # type (the ORM ``IngestRun``) and not the Pydantic schema. Validate
    # explicitly so the type checker and the runtime agree.
    return IngestRunOut.model_validate(run, from_attributes=True)


@router.get("/sources", response_model=list[SourceConnectorOut])
async def list_sources() -> list[SourceConnectorOut]:
    return [SourceConnectorOut(name=name) for name in sorted(connector_map().keys())]
