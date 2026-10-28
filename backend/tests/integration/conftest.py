"""Fixture Testcontainers dùng chung cho test tích hợp cô lập dữ liệu
(T-504 §3, §5 bước 1-2) — PostgreSQL 16 + pgvector (chạy alembic thật,
có policy RLS của T-104) và Redis 7 (phiên thật qua `app.modules.identity.sessions`).

Cần Docker Engine để chạy — môi trường triển khai các task này không có
Docker (xem "Ghi chú triển khai thực tế" trong các file task T-005, T-101).
Test được viết đầy đủ và đúng; tự `pytest.skip` nếu không khởi động được
container thay vì giả vờ xanh.
"""

from __future__ import annotations

import json
import pathlib
import time
from collections.abc import Iterator
from dataclasses import dataclass
from uuid import uuid4

import pytest
import sqlalchemy as sa

try:
    from testcontainers.community.postgres import PostgresContainer
    from testcontainers.community.redis import RedisContainer
except ImportError:  # pragma: no cover
    PostgresContainer = None  # type: ignore[assignment,misc]
    RedisContainer = None  # type: ignore[assignment,misc]

pytestmark = pytest.mark.skipif(
    PostgresContainer is None or RedisContainer is None,
    reason="testcontainers chưa được cài trong môi trường này",
)

_CWD_APP_PASSWORD = "cwd_app_test_only"  # noqa: S105 - test-only, container ngắn hạn


@dataclass(frozen=True)
class SeededDocument:
    id: object


def _run_alembic_upgrade(admin_url: str) -> None:
    from alembic import command
    from alembic.config import Config

    backend_root = pathlib.Path(__file__).parents[2]
    cfg = Config(str(backend_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_root / "migrations"))
    cfg.set_main_option("sqlalchemy.url", admin_url)
    command.upgrade(cfg, "head")


@pytest.fixture(scope="module")
def isolation_stack() -> Iterator[dict[str, str]]:
    try:
        pg = PostgresContainer("pgvector/pgvector:pg16")
        pg.start()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Không khởi động được container PostgreSQL (cần Docker): {exc}")
        return
    try:
        redis_container = RedisContainer()
        redis_container.start()
    except Exception as exc:  # noqa: BLE001
        pg.stop()
        pytest.skip(f"Không khởi động được container Redis (cần Docker): {exc}")
        return

    try:
        admin_url = pg.get_connection_url().replace("psycopg2", "asyncpg")
        _run_alembic_upgrade(admin_url)

        sync_admin_url = admin_url.replace("+asyncpg", "")
        engine = sa.create_engine(sync_admin_url)
        with engine.begin() as conn:
            conn.execute(
                sa.text(f"ALTER ROLE cwd_app LOGIN PASSWORD '{_CWD_APP_PASSWORD}'")  # noqa: S608
            )
        engine.dispose()

        parsed = sa.engine.make_url(admin_url)
        app_database_url = str(
            parsed.set(
                username="cwd_app",
                password=_CWD_APP_PASSWORD,
                drivername="postgresql+asyncpg",
            )
        )
        redis_host = redis_container.get_container_host_ip()
        redis_port = redis_container.get_exposed_port(redis_container.port)
        redis_url = f"redis://{redis_host}:{redis_port}/0"

        yield {
            "database_url": app_database_url,
            "admin_sync_url": sync_admin_url,
            "redis_url": redis_url,
        }
    finally:
        redis_container.stop()
        pg.stop()


@pytest.fixture
def app_env(isolation_stack: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    import app.core.config as config_module
    import app.core.db as db_module
    import app.core.redis_client as redis_client_module

    monkeypatch.setenv("DATABASE_URL", isolation_stack["database_url"])
    monkeypatch.setenv("REDIS_URL", isolation_stack["redis_url"])
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    config_module.get_settings.cache_clear()
    db_module._engine = None
    db_module._session_factory = None
    redis_client_module.get_redis.cache_clear()

    yield

    config_module.get_settings.cache_clear()
    db_module._engine = None
    db_module._session_factory = None
    redis_client_module.get_redis.cache_clear()


@pytest.fixture
def app_client_factory(app_env: None) -> Iterator[object]:
    from contextlib import ExitStack

    from fastapi.testclient import TestClient

    from app.api.main import app as fastapi_app

    with ExitStack() as stack:

        def _make() -> TestClient:
            client = TestClient(fastapi_app)
            stack.enter_context(client)
            return client

        yield _make


def _insert_user(admin_sync_url: str, *, email: str) -> str:
    engine = sa.create_engine(admin_sync_url)
    try:
        with engine.begin() as conn:
            user_id = conn.execute(
                sa.text(
                    "INSERT INTO app_user (id, email, active) "
                    "VALUES (gen_random_uuid(), :email, true) RETURNING id"
                ),
                {"email": email},
            ).scalar_one()
    finally:
        engine.dispose()
    return str(user_id)


def _insert_document(admin_sync_url: str, *, owner_id: str, name: str) -> str:
    engine = sa.create_engine(admin_sync_url)
    try:
        with engine.begin() as conn:
            document_id = conn.execute(
                sa.text(
                    "INSERT INTO document (id, owner_id, name, size_bytes, status, "
                    "blob_key, sha256, uploaded_at) VALUES "
                    "(gen_random_uuid(), :owner, :name, 100, 'ready', :blob_key, "
                    "repeat('a', 64), now()) RETURNING id"
                ),
                {"owner": owner_id, "name": name, "blob_key": f"owner/{owner_id}/{uuid4()}.pdf"},
            ).scalar_one()
    finally:
        engine.dispose()
    return str(document_id)


def _create_session(redis_url: str, *, user_id: str) -> tuple[str, str]:
    import redis as redis_sync

    sid = uuid4().hex
    csrf_token = uuid4().hex
    now = time.time()
    payload = {
        "user_id": user_id,
        "csrf_token": csrf_token,
        "roles": [],
        "created_at": now,
        "last_seen_at": now,
    }
    client = redis_sync.Redis.from_url(redis_url, decode_responses=True)
    try:
        client.set(f"session:{sid}", json.dumps(payload), ex=2 * 60 * 60)
    finally:
        client.close()
    return sid, csrf_token


def _client_as(app_client_factory, isolation_stack: dict[str, str], *, user_id: str):
    sid, csrf_token = _create_session(isolation_stack["redis_url"], user_id=user_id)
    client = app_client_factory()
    client.cookies.set("cwd_sid", sid)
    client.headers.update({"X-CSRF-Token": csrf_token})
    return client


@pytest.fixture
def seeded_documents(isolation_stack: dict[str, str]) -> dict[str, list[SeededDocument]]:
    owner_a = _insert_user(isolation_stack["admin_sync_url"], email="owner-a@example.com")
    owner_b = _insert_user(isolation_stack["admin_sync_url"], email="owner-b@example.com")
    doc_a = _insert_document(isolation_stack["admin_sync_url"], owner_id=owner_a, name="A.pdf")
    doc_b = _insert_document(isolation_stack["admin_sync_url"], owner_id=owner_b, name="B.pdf")
    return {
        "owner_a": owner_a,
        "owner_b": owner_b,
        "a": [SeededDocument(id=doc_a)],
        "b": [SeededDocument(id=doc_b)],
    }


@pytest.fixture
def client_a(
    app_client_factory, isolation_stack: dict[str, str], seeded_documents: dict[str, object]
):
    return _client_as(app_client_factory, isolation_stack, user_id=seeded_documents["owner_a"])


@pytest.fixture
def client_b(
    app_client_factory, isolation_stack: dict[str, str], seeded_documents: dict[str, object]
):
    return _client_as(app_client_factory, isolation_stack, user_id=seeded_documents["owner_b"])
