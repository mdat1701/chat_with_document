"""Kiểm thử `app.modules.identity.repository` trên PostgreSQL thật qua
Testcontainers (T-101 §7) — xác nhận CITEXT (so khớp email không phân
biệt hoa/thường) và UUID hoạt động đúng, điều test đơn vị với mock
không chứng minh được.

Cần Docker — xem "Ghi chú triển khai thực tế" trong
docs/implement/tasks/T-101_oidc-login.md nếu chưa chạy được.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.db import Base
from app.modules.identity import repository
from app.modules.identity.models import AppUser

try:
    from testcontainers.community.postgres import PostgresContainer
except ImportError:  # pragma: no cover
    PostgresContainer = None  # type: ignore[assignment,misc]

pytestmark = pytest.mark.skipif(
    PostgresContainer is None, reason="testcontainers chưa được cài trong môi trường này"
)


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    try:
        container = PostgresContainer("pgvector/pgvector:pg16")
        container.start()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Không khởi động được container PostgreSQL (cần Docker): {exc}")

    try:
        url = container.get_connection_url().replace("psycopg2", "asyncpg")
        engine = create_async_engine(url)
        async with engine.begin() as conn:
            await conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS citext"))
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            yield session
        await engine.dispose()
    finally:
        container.stop()


async def test_get_by_email_is_case_insensitive(db_session: AsyncSession) -> None:
    user = AppUser(email="User@Example.com", active=True)
    db_session.add(user)
    await db_session.commit()

    found = await repository.get_by_email(db_session, "user@example.com")
    assert found is not None
    assert found.id == user.id


async def test_get_by_oidc_subject_returns_none_when_not_linked(db_session: AsyncSession) -> None:
    user = AppUser(email="a@example.com", active=True, oidc_subject=None)
    db_session.add(user)
    await db_session.commit()

    assert await repository.get_by_oidc_subject(db_session, "some-sub") is None


async def test_link_oidc_subject_persists_and_keeps_existing_display_name(
    db_session: AsyncSession,
) -> None:
    user = AppUser(email="a@example.com", active=True, display_name="Tên Cũ")
    db_session.add(user)
    await db_session.commit()

    await repository.link_oidc_subject(
        db_session, user=user, oidc_subject="sub-1", display_name="Tên Mới Từ IdP"
    )
    await db_session.commit()

    refetched = await repository.get_by_oidc_subject(db_session, "sub-1")
    assert refetched is not None
    assert refetched.display_name == "Tên Cũ"  # không ghi đè tên đã có
