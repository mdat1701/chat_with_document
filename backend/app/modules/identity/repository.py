"""Truy cập `app_user`/`user_role` (T-101 §4-5). Chỉ `service.py` trong
cùng module gọi vào đây — module khác không import trực tiếp
(nguyên tắc ranh giới SADD §2.2.1)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import AppUser, UserRole


async def get_by_oidc_subject(session: AsyncSession, oidc_subject: str) -> AppUser | None:
    result = await session.execute(select(AppUser).where(AppUser.oidc_subject == oidc_subject))
    return result.scalar_one_or_none()


async def get_by_email(session: AsyncSession, email: str) -> AppUser | None:
    result = await session.execute(select(AppUser).where(AppUser.email == email))
    return result.scalar_one_or_none()


async def get_by_id(session: AsyncSession, user_id: uuid.UUID) -> AppUser | None:
    result = await session.execute(select(AppUser).where(AppUser.id == user_id))
    return result.scalar_one_or_none()


async def link_oidc_subject(
    session: AsyncSession, *, user: AppUser, oidc_subject: str, display_name: str | None
) -> None:
    """Lần đăng nhập đầu của tài khoản đã được cấp quyền bằng email
    (T-103) nhưng chưa từng đăng nhập — điền `oidc_subject` (T-101 §5
    bước 5)."""
    user.oidc_subject = oidc_subject
    if display_name and not user.display_name:
        user.display_name = display_name
    await session.flush()


async def get_roles(session: AsyncSession, user_id: uuid.UUID) -> list[str]:
    result = await session.execute(select(UserRole.role).where(UserRole.user_id == user_id))
    return list(result.scalars().all())
