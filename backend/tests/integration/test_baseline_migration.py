"""Kiểm thử migration 0001_baseline trên PostgreSQL thật qua
Testcontainers (T-005 §5 bước 9, §7).

Cần Docker Engine để chạy — môi trường triển khai task này không có
Docker (xem "Ghi chú triển khai thực tế" trong
docs/implement/tasks/T-005_database-baseline.md). Test được viết đầy
đủ và đúng, `pytest.importorskip`/skip tự động nếu không khởi động
được container thay vì giả vờ xanh.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
import sqlalchemy as sa

try:
    from testcontainers.community.postgres import PostgresContainer
except ImportError:  # pragma: no cover
    PostgresContainer = None  # type: ignore[assignment,misc]


pytestmark = pytest.mark.skipif(
    PostgresContainer is None, reason="testcontainers chưa được cài trong môi trường này"
)


@pytest.fixture(scope="module")
def pg_url() -> Iterator[str]:
    try:
        with PostgresContainer("pgvector/pgvector:pg16") as pg:
            yield pg.get_connection_url().replace("psycopg2", "asyncpg")
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Không khởi động được container PostgreSQL (cần Docker): {exc}")


def _run_alembic_upgrade(database_url: str) -> None:
    import pathlib

    from alembic import command
    from alembic.config import Config

    backend_root = pathlib.Path(__file__).parents[2]
    cfg = Config(str(backend_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_root / "migrations"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(cfg, "head")


def test_upgrade_creates_eight_tables(pg_url: str) -> None:
    _run_alembic_upgrade(pg_url)

    sync_url = pg_url.replace("+asyncpg", "")
    engine = sa.create_engine(sync_url)
    with engine.connect() as conn:
        tables = (
            conn.execute(
                sa.text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' ORDER BY table_name"
                )
            )
            .scalars()
            .all()
        )

    expected = {
        "analytics_event",
        "answer",
        "app_user",
        "audit_log",
        "chunk",
        "document",
        "feedback",
        "user_role",
    }
    assert expected.issubset(set(tables))


def test_cwd_app_role_does_not_have_bypassrls(pg_url: str) -> None:
    sync_url = pg_url.replace("+asyncpg", "")
    engine = sa.create_engine(sync_url)
    with engine.connect() as conn:
        value = conn.execute(
            sa.text("SELECT rolbypassrls FROM pg_roles WHERE rolname = 'cwd_app'")
        ).scalar_one()
    assert value is False


def test_cwd_worker_role_has_bypassrls(pg_url: str) -> None:
    sync_url = pg_url.replace("+asyncpg", "")
    engine = sa.create_engine(sync_url)
    with engine.connect() as conn:
        value = conn.execute(
            sa.text("SELECT rolbypassrls FROM pg_roles WHERE rolname = 'cwd_worker'")
        ).scalar_one()
    assert value is True


def test_downgrade_then_upgrade_again_is_clean(pg_url: str) -> None:
    import pathlib

    from alembic import command
    from alembic.config import Config

    backend_root = pathlib.Path(__file__).parents[2]
    cfg = Config(str(backend_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_root / "migrations"))
    cfg.set_main_option("sqlalchemy.url", pg_url)

    command.downgrade(cfg, "-1")
    command.upgrade(cfg, "head")


def test_duplicate_name_same_owner_is_rejected_case_insensitive(pg_url: str) -> None:
    sync_url = pg_url.replace("+asyncpg", "")
    engine = sa.create_engine(sync_url)
    with engine.begin() as conn:
        owner_id = conn.execute(
            sa.text(
                "INSERT INTO app_user (id, email, active) "
                "VALUES (gen_random_uuid(), 'u@example.com', true) RETURNING id"
            )
        ).scalar_one()
        conn.execute(
            sa.text(
                "INSERT INTO document (id, owner_id, name, size_bytes, status, "
                "blob_key, sha256, uploaded_at) VALUES "
                "(gen_random_uuid(), :owner, 'Bao cao.pdf', 100, 'ready', 'k', "
                "repeat('a', 64), now())"
            ),
            {"owner": owner_id},
        )
        with pytest.raises(sa.exc.IntegrityError):
            conn.execute(
                sa.text(
                    "INSERT INTO document (id, owner_id, name, size_bytes, status, "
                    "blob_key, sha256, uploaded_at) VALUES "
                    "(gen_random_uuid(), :owner, 'bao cao.pdf', 100, 'ready', 'k2', "
                    "repeat('b', 64), now())"
                ),
                {"owner": owner_id},
            )
