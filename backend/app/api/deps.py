"""Dependency dùng chung cho router (T-008 §5 bước 9).

`get_current_user` là STUB Sprint 0 — T-102 thay bằng bản thật (đọc
cookie `cwd_sid` → tra phiên Redis → trả `CurrentUser`). Chữ ký hàm
KHÔNG được đổi để router của Sprint 1 không phải sửa lại.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import session_scope
from app.core.redis_client import get_redis
from app.ports.oidc_port import OIDCPort


class CurrentUser(BaseModel):
    id: str
    email: str
    roles: list[str] = []


def assert_stub_auth_allowed() -> None:
    """Gọi ở sự kiện khởi động app (T-008 §6 "Stub auth bị lọt lên
    staging/production"). Dừng tiến trình ngay nếu stub auth còn được
    dùng ngoài môi trường local."""
    settings = get_settings()
    if settings.app_env != "local":
        raise RuntimeError(
            "get_current_user() vẫn là STUB (T-008) nhưng app_env="
            f"{settings.app_env!r} != 'local'. Không được chạy stub auth "
            "ngoài local — hoàn thành T-102 trước khi deploy staging/production."
        )


async def get_current_user() -> CurrentUser:
    """STUB Sprint 0: trả user cố định từ biến môi trường `DEV_USER_ID`
    (mặc định một UUID cố định cho local). T-102 thay thế toàn bộ thân
    hàm bằng: đọc cookie `cwd_sid` → tra phiên Redis → `CurrentUser`
    thật — KHÔNG đổi chữ ký hàm.
    """
    user_id = os.environ.get("DEV_USER_ID", "00000000-0000-0000-0000-000000000001")
    return CurrentUser(id=user_id, email="dev@example.com", roles=["user"])


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
