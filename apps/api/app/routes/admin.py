"""Administrative endpoints — manual scheduler kick for ops/debugging."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_user
from app.deps import DbSession
from app.models import User
from app.schemas import SchedulerRunOut
from app.services.scheduler import run_once

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/run-scheduler", response_model=SchedulerRunOut)
async def run_scheduler_once(
    db: DbSession,
    frequency: str = Query(default="daily"),
    current_user: User = Depends(get_current_user),
) -> SchedulerRunOut:
    if current_user.role != "employer":
        raise HTTPException(status_code=403, detail="Only employers can run scheduler")
    if frequency not in {"daily", "weekly"}:
        raise HTTPException(status_code=400, detail="frequency must be daily or weekly")
    result = await run_once(db, digest_frequency=frequency)
    return SchedulerRunOut(**asdict(result))
