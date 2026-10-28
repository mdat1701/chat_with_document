"""Dependency dùng chung cho router (T-008 §5 bước 9).

`get_current_user` là STUB Sprint 0 — T-102 thay bằng bản thật (đọc
cookie `cwd_sid` → tra phiên Redis → trả `CurrentUser`). Chữ ký hàm
KHÔNG được đổi để router của Sprint 1 không phải sửa lại.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from pydantic import BaseModel, Field
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import session_scope
from app.core.errors import DomainError
from app.core.redis_client import get_redis
from app.modules.identity import repository, sessions
from app.ports.llm_port import LLMPort
from app.ports.oidc_port import OIDCPort


class CurrentUser(BaseModel):
    id: str
    email: str
    display_name: str | None = None
    roles: list[str] = Field(default_factory=list)
    csrf_token: str


def assert_stub_auth_allowed() -> None:
    """Reject an incompletely configured non-local deployment.

    The authentication dependency is real now; this remains as a safety
    guard for staging configurations that still have no IdP settings.
    """
    settings = get_settings()
    if settings.app_env != "local" and not (
        settings.oidc_issuer and settings.oidc_client_id and settings.oidc_client_secret
    ):
        raise RuntimeError("STUB auth configuration is not allowed outside local")


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Một session mỗi request, dùng vai trò `cwd_app` (T-005/T-104)."""
    async with session_scope() as session:
        yield session


def get_redis_client() -> Redis:
    return get_redis()


def get_oidc_port() -> OIDCPort:
    """Trả về adapter OIDC thật (T-101). Test ghi đè qua
    `app.dependency_overrides[get_oidc_port]` bằng một `FakeOIDCAdapter`."""
    from app.adapters.authlib_oidc import get_oidc_adapter

    return get_oidc_adapter()


def get_llm_port() -> LLMPort:
    """Chọn adapter LLM theo `settings.llm_provider` (T-301). `modules.qa`
    chỉ biết `LLMPort` — việc chọn adapter cụ thể thuộc tầng `api` (nguyên
    tắc P-01), KHÔNG được quyết định bên trong `modules/qa/service.py`.
    Test ghi đè qua `app.dependency_overrides[get_llm_port]`."""
    from app.adapters.openai_llm import FakeLLM, OpenAICompatibleLLM

    settings = get_settings()
    if settings.llm_provider == "fake":
        return FakeLLM()
    return OpenAICompatibleLLM()


async def get_current_user(
    request: Request,
    redis: Annotated[Redis, Depends(get_redis_client)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CurrentUser:
    """Resolve the authenticated user from the server-side session."""
    sid = request.cookies.get("cwd_sid")
    if not sid:
        raise DomainError("SESSION_EXPIRED")

    session_data = await sessions.get_session(redis, sid)
    if session_data is None:
        raise DomainError("SESSION_EXPIRED")
    await sessions.touch_session(redis, sid, session_data)

    try:
        user_id = uuid.UUID(session_data.user_id)
    except ValueError as exc:
        raise DomainError("SESSION_EXPIRED") from exc

    user = await repository.get_by_id(session, user_id)
    if user is None or not user.active:
        raise DomainError("NOT_AUTHORIZED")

    # Bind the authenticated identity to this transaction for PostgreSQL RLS.
    await session.execute(
        text("SELECT set_config('app.user_id', :user_id, true)"),
        {"user_id": str(user.id)},
    )
    roles = await repository.get_roles(session, user.id)
    request.state.user_id = str(user.id)
    return CurrentUser(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        roles=roles,
        csrf_token=session_data.csrf_token,
    )
