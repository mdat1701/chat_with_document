from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_db_session
from app.modules.analytics.service import record_event

router = APIRouter(tags=["analytics"])


class ClientEvent(BaseModel):
    event_name: str
    timestamp: datetime | None = None
    props: dict[str, object] = Field(default_factory=dict)


class EventBatch(BaseModel):
    events: list[ClientEvent] = Field(min_length=1, max_length=20)


@router.post("/events", status_code=204)
async def receive_events(
    payload: EventBatch,
    request: Request,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    sid = request.cookies.get("cwd_sid")
    for event in payload.events:
        await record_event(
            session,
            event.event_name,
            user_id=UUID(current_user.id),
            sid=sid,
            props=event.props,
        )
    await session.commit()
    return Response(status_code=204)
