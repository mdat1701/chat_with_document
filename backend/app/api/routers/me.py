"""Authenticated identity endpoint (T-102, API-01)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, get_current_user
from app.core.metrics import auth_me_total

router = APIRouter(tags=["identity"])


@router.get("/me", response_model=CurrentUser)
async def get_me(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    auth_me_total.labels(outcome="success").inc()
    return current_user
