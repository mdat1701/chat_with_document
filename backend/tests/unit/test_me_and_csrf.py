"""Kiểm thử `GET /me` và middleware CSRF (T-102) qua `TestClient` thật —
trước phiên này không có test tự động nào cho `/me` hay cho hành vi
chặn/cho-qua thật của `csrf_protection` (chỉ test `/auth/*` tồn tại).
Dùng `fakeredis` cho phiên thật và `AsyncMock`/`MagicMock` tuần tự cho
`AsyncSession.execute()`, cùng kỹ thuật đã dùng ở `test_auth_router.py`/
`test_documents_router.py`.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fakeredis import FakeAsyncRedis
from fastapi.testclient import TestClient

from app.api import main as main_module
from app.api.deps import get_db_session, get_redis_client
from app.api.main import app
from app.modules.identity.models import AppUser

_USER_ID = uuid.uuid4()
_SID = "test-sid-abcdef"
_CSRF_TOKEN = "test-csrf-token-xyz"


def _session_payload(*, created_at: float | None = None) -> dict[str, Any]:
    now = time.time()
    return {
        "user_id": str(_USER_ID),
        "csrf_token": _CSRF_TOKEN,
        "roles": ["user"],
        "created_at": created_at if created_at is not None else now,
        "last_seen_at": now,
    }


class _FakeScalars:
    def __init__(self, values: list[Any]) -> None:
        self._values = values

    def all(self) -> list[Any]:
        return self._values


class _FakeScalarResult:
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

    async def execute(self, _statement: object, _params: object = None) -> Any:
        value = self._results.pop(0)
        if value == "raw":
            return _FakeScalarResult(None)
        return _FakeScalarResult(value)


@pytest.fixture
async def fake_redis() -> FakeAsyncRedis:
    client = FakeAsyncRedis()
    yield client
    await client.aclose()


def _make_client(fake_redis: FakeAsyncRedis, session: _SequentialSession) -> TestClient:
    async def _fake_db_session() -> Any:
        yield session

    app.dependency_overrides[get_redis_client] = lambda: fake_redis
    app.dependency_overrides[get_db_session] = _fake_db_session
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _clear_overrides() -> Any:
    yield
    app.dependency_overrides.clear()


async def test_get_me_with_valid_session_returns_200_with_schema(
    fake_redis: FakeAsyncRedis,
) -> None:
    await fake_redis.set(f"session:{_SID}", json.dumps(_session_payload()), ex=7200)
    user = AppUser(id=_USER_ID, email="u@example.com", display_name="Người dùng", active=True)
    session = _SequentialSession([user, "raw", []])
    client = _make_client(fake_redis, session)

    response = client.get("/api/v1/me", cookies={"cwd_sid": _SID})

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(_USER_ID)
    assert body["email"] == "u@example.com"
    assert body["roles"] == []
    assert body["csrf_token"] == _CSRF_TOKEN
    assert "sid" not in body
    assert "oidc_subject" not in body


def test_get_me_without_cookie_returns_401_session_expired(fake_redis: FakeAsyncRedis) -> None:
    session = _SequentialSession([])
    client = _make_client(fake_redis, session)

    response = client.get("/api/v1/me")

    assert response.status_code == 401
    assert response.json()["code"] == "SESSION_EXPIRED"


async def test_get_me_after_session_deleted_from_redis_returns_401(
    fake_redis: FakeAsyncRedis,
) -> None:
    # Không `set` session nào — mô phỏng đã bị xóa khỏi Redis (hết TTL
    # hoặc bị T-103 thu hồi).
    session = _SequentialSession([])
    client = _make_client(fake_redis, session)

    response = client.get("/api/v1/me", cookies={"cwd_sid": _SID})

    assert response.status_code == 401
    assert response.json()["code"] == "SESSION_EXPIRED"


async def test_get_me_with_inactive_user_returns_403_not_authorized(
    fake_redis: FakeAsyncRedis,
) -> None:
    await fake_redis.set(f"session:{_SID}", json.dumps(_session_payload()), ex=7200)
    inactive_user = AppUser(id=_USER_ID, email="u@example.com", active=False)
    session = _SequentialSession([inactive_user])
    client = _make_client(fake_redis, session)

    response = client.get("/api/v1/me", cookies={"cwd_sid": _SID})

    assert response.status_code == 403
    assert response.json()["code"] == "NOT_AUTHORIZED"


async def test_get_me_twice_returns_same_csrf_token(fake_redis: FakeAsyncRedis) -> None:
    await fake_redis.set(f"session:{_SID}", json.dumps(_session_payload()), ex=7200)
    user = AppUser(id=_USER_ID, email="u@example.com", active=True)
    client = _make_client(fake_redis, _SequentialSession([user, "raw", [], user, "raw", []]))

    first = client.get("/api/v1/me", cookies={"cwd_sid": _SID})
    second = client.get("/api/v1/me", cookies={"cwd_sid": _SID})

    assert first.json()["csrf_token"] == second.json()["csrf_token"] == _CSRF_TOKEN


async def test_post_without_csrf_token_is_rejected_with_403(
    fake_redis: FakeAsyncRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    await fake_redis.set(f"session:{_SID}", json.dumps(_session_payload()), ex=7200)
    monkeypatch.setattr(main_module, "get_redis", lambda: fake_redis)
    client = _make_client(fake_redis, _SequentialSession([]))

    response = client.post("/api/v1/conversations", cookies={"cwd_sid": _SID})

    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_INVALID"


async def test_post_with_wrong_csrf_token_is_rejected_with_403(
    fake_redis: FakeAsyncRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    await fake_redis.set(f"session:{_SID}", json.dumps(_session_payload()), ex=7200)
    monkeypatch.setattr(main_module, "get_redis", lambda: fake_redis)
    client = _make_client(fake_redis, _SequentialSession([]))

    response = client.post(
        "/api/v1/conversations",
        cookies={"cwd_sid": _SID},
        headers={"X-CSRF-Token": "khong-dung"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "CSRF_INVALID"


async def test_post_without_session_cookie_is_not_blocked_by_csrf_middleware(
    fake_redis: FakeAsyncRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Không có `cwd_sid` -> middleware để tầng xác thực bình thường xử
    lý (401 `SESSION_EXPIRED` từ `get_current_user`), không phải 403
    CSRF — tránh lẫn hai lớp lỗi khác nhau."""
    monkeypatch.setattr(main_module, "get_redis", lambda: fake_redis)
    client = _make_client(fake_redis, _SequentialSession([]))

    response = client.post("/api/v1/conversations")

    assert response.status_code != 403
