"""Kiểm thử `GET /config` (T-105) qua `TestClient` thật — trước phiên
này không có test tự động nào cho endpoint này."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fakeredis import FakeAsyncRedis
from fastapi.testclient import TestClient

from app.api.deps import get_db_session, get_redis_client
from app.api.main import app
from app.modules.identity.models import AppUser

_USER_ID = uuid.uuid4()
_SID = "config-test-sid"


class _FakeScalars:
    def __init__(self, values: list[Any]) -> None:
        self._values = values

    def all(self) -> list[Any]:
        return self._values


class _FakeResult:
    def __init__(self, value: Any) -> None:
        self._value = value

    def scalar_one_or_none(self) -> Any:
        return self._value

    def scalars(self) -> _FakeScalars:
        return _FakeScalars(self._value if isinstance(self._value, list) else [])


class _SequentialSession:
    def __init__(self, results: list[Any]) -> None:
        self._results = list(results)
        self.add = MagicMock()
        self.commit = AsyncMock()

    async def execute(self, _statement: object, _params: object = None) -> _FakeResult:
        return _FakeResult(self._results.pop(0))


@pytest.fixture
async def fake_redis() -> FakeAsyncRedis:
    client = FakeAsyncRedis()
    yield client
    await client.aclose()


@pytest.fixture(autouse=True)
def _clear_overrides() -> Any:
    yield
    app.dependency_overrides.clear()


async def test_get_config_without_session_returns_401(fake_redis: FakeAsyncRedis) -> None:
    app.dependency_overrides[get_redis_client] = lambda: fake_redis

    async def _fake_db() -> Any:
        yield _SequentialSession([])

    app.dependency_overrides[get_db_session] = _fake_db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/api/v1/config")

    assert response.status_code == 401
    assert response.json()["code"] == "SESSION_EXPIRED"


async def test_get_config_with_session_returns_expected_shape(fake_redis: FakeAsyncRedis) -> None:
    now = time.time()
    await fake_redis.set(
        f"session:{_SID}",
        json.dumps(
            {
                "user_id": str(_USER_ID),
                "csrf_token": "tok",
                "roles": ["user"],
                "created_at": now,
                "last_seen_at": now,
            }
        ),
        ex=7200,
    )
    user = AppUser(id=_USER_ID, email="u@example.com", active=True)
    app.dependency_overrides[get_redis_client] = lambda: fake_redis

    async def _fake_db() -> Any:
        yield _SequentialSession([user, None, []])

    app.dependency_overrides[get_db_session] = _fake_db
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/api/v1/config", cookies={"cwd_sid": _SID})

    assert response.status_code == 200
    body = response.json()
    for field in (
        "max_file_size_bytes",
        "max_documents",
        "max_pages",
        "retention_days",
        "max_question_length",
        "answer_timeout_ms",
        "features",
        "retrieval",
        "supported_languages",
    ):
        assert field in body
    assert isinstance(body["max_file_size_bytes"], int)
    assert isinstance(body["supported_languages"], list)
    assert "citation_page_numbers" in body["features"]
    assert response.headers["cache-control"] == "private, max-age=300"
