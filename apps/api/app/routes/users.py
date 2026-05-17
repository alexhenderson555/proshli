"""Current-user introspection endpoints."""

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.models import User
from app.schemas import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> User:
    """Return the authenticated user.

    The response is shaped by ``UserOut`` via FastAPI's ``response_model``;
    the typed return is the ORM instance so mypy stays happy without an
    explicit conversion.
    """
    return current_user
