"""Hạ tầng CSDL dùng chung: `Base` khai báo (DeclarativeBase) và engine
async. Mọi `modules/<m>/models.py` kế thừa `Base` từ đây — việc import
`app.core` từ `app.modules.*` được phép (xem `pyproject.toml`
`[[tool.importlinter.contracts]]`).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Base chung cho mọi ORM model của hệ thống."""


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_worker_engine: AsyncEngine | None = None
_worker_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Engine dùng cho `api` — kết nối bằng vai trò `cwd_app` (KHÔNG
    BYPASSRLS, T-005)."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Một transaction / request. T-104 sẽ bổ sung `SET LOCAL app.user_id`
    ngay sau khi mở session, trước khi chạy câu lệnh đầu tiên.
    """
    async with get_session_factory()() as session:
        yield session


def get_worker_engine() -> AsyncEngine:
    """Engine dùng cho `worker` — kết nối bằng vai trò `cwd_worker` (có
    BYPASSRLS, T-005/T-006); worker tự lọc theo `document_id` tường
    minh thay vì dựa vào RLS."""
    global _worker_engine
    if _worker_engine is None:
        _worker_engine = create_async_engine(
            get_settings().worker_database_url_or_default(), pool_pre_ping=True
        )
    return _worker_engine


def get_worker_session_factory() -> async_sessionmaker[AsyncSession]:
    global _worker_session_factory
    if _worker_session_factory is None:
        _worker_session_factory = async_sessionmaker(get_worker_engine(), expire_on_commit=False)
    return _worker_session_factory


@asynccontextmanager
async def worker_session_scope() -> AsyncIterator[AsyncSession]:
    """Dùng trong task Celery (T-201, T-207, ...) — KHÔNG dùng
    `session_scope()` (vai trò `cwd_app`) trong worker."""
    async with get_worker_session_factory()() as session:
        yield session
