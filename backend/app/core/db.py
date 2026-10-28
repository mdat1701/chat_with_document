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


def get_engine() -> AsyncEngine:
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
