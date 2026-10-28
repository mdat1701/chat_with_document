"""Kiểm thử `POST /documents` (T-108) qua `TestClient` thật — trước
phiên này router này không có test tự động riêng (chỉ xác nhận bằng đọc
code). Dùng `fakeredis` cho rate limit, `AsyncMock`/`MagicMock` tuần tự
cho `AsyncSession.execute()` (cùng kỹ thuật đã dùng ở `test_auth_router.py`),
và một thư mục tạm cho `blob_dir` — không cần Postgres thật.
"""

from __future__ import annotations

import io
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fakeredis import FakeAsyncRedis
from fastapi.testclient import TestClient

from app.api import deps as deps_module
from app.api.deps import CurrentUser, get_current_user, get_db_session
from app.api.main import app
from app.api.routers import documents as documents_module
from app.modules.identity.models import AppUser
from app.ports.queue_port import QueuePort


class _FakeSettings:
    app_env = "local"
    max_file_size_bytes = 20 * 1024 * 1024
    max_documents = 50
    max_pages = 300
    retention_days = 90

    def __init__(self, blob_dir: str) -> None:
        self.blob_dir = blob_dir


class _FakeScalarResult:
    def __init__(self, value: Any) -> None:
        self._value = value

    def scalar_one_or_none(self) -> Any:
        return self._value

    def scalar_one(self) -> Any:
        return self._value


class _SequentialSession:
    """Trả lần lượt các kết quả đã khai báo cho mỗi lệnh gọi `execute()`,
    theo đúng thứ tự `upload_document` gọi (owner FOR UPDATE -> đếm hạn
    mức -> kiểm tra trùng tên)."""

    def __init__(self, results: list[Any]) -> None:
        self._results = list(results)
        self.added: list[object] = []
        self.commit = AsyncMock()
        self.rollback = AsyncMock()
        self.add = MagicMock(side_effect=self.added.append)

    async def execute(self, _statement: object) -> _FakeScalarResult:
        return _FakeScalarResult(self._results.pop(0))


class _FakeQueue(QueuePort):
    def __init__(self) -> None:
        self.enqueued: list[tuple[str, dict[str, Any]]] = []

    def enqueue(self, task_name: str, payload: dict[str, Any]) -> str:
        self.enqueued.append((task_name, payload))
        return "fake-task-id"


_OWNER_ID = uuid.uuid4()
_CURRENT_USER = CurrentUser(id=str(_OWNER_ID), email="u@example.com", csrf_token="tok")


@pytest.fixture
def fake_owner() -> AppUser:
    return AppUser(id=_OWNER_ID, email="u@example.com", active=True)


@pytest.fixture
def blob_dir(tmp_path: Path) -> Path:
    return tmp_path / "blobs"


def _make_client(
    monkeypatch: pytest.MonkeyPatch, session: _SequentialSession, blob_dir: Path
) -> tuple[TestClient, _FakeQueue]:
    fake_redis = FakeAsyncRedis()
    fake_queue = _FakeQueue()
    settings = _FakeSettings(blob_dir=str(blob_dir))

    monkeypatch.setattr(documents_module, "get_redis", lambda: fake_redis)
    monkeypatch.setattr(documents_module, "get_settings", lambda: settings)
    monkeypatch.setattr(deps_module, "get_settings", lambda: settings)

    async def _fake_db_session() -> Any:
        yield session

    app.dependency_overrides[get_current_user] = lambda: _CURRENT_USER
    app.dependency_overrides[get_db_session] = _fake_db_session
    app.dependency_overrides[documents_module.get_queue] = lambda: fake_queue

    client = TestClient(app, raise_server_exceptions=False)
    return client, fake_queue


@pytest.fixture(autouse=True)
def _clear_overrides() -> Any:
    yield
    app.dependency_overrides.clear()


def _pdf_bytes(size: int = 1024) -> bytes:
    return b"%PDF-1.4\n" + b"0" * size


def test_valid_pdf_upload_returns_201_and_enqueues_ingestion(
    monkeypatch: pytest.MonkeyPatch, fake_owner: AppUser, blob_dir: Path
) -> None:
    session = _SequentialSession([fake_owner, 0, None])
    client, queue = _make_client(monkeypatch, session, blob_dir)

    response = client.post(
        "/api/v1/documents",
        files={"file": ("HopDong.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")},
        headers={"Content-Length": str(len(_pdf_bytes()))},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "processing"
    assert body["page_count"] is None
    assert queue.enqueued and queue.enqueued[0][0] == "ingestion.process"
    assert session.commit.await_count == 1


def test_non_pdf_magic_bytes_returns_415(
    monkeypatch: pytest.MonkeyPatch, fake_owner: AppUser, blob_dir: Path
) -> None:
    session = _SequentialSession([])  # không đọc tới DB vì bị chặn trước
    client, _queue = _make_client(monkeypatch, session, blob_dir)

    response = client.post(
        "/api/v1/documents",
        files={"file": ("fake.pdf", io.BytesIO(b"\x89PNG not a pdf"), "application/pdf")},
    )

    assert response.status_code == 415
    assert response.json()["code"] == "FILE_NOT_PDF"


def test_quota_exceeded_returns_422(
    monkeypatch: pytest.MonkeyPatch, fake_owner: AppUser, blob_dir: Path
) -> None:
    session = _SequentialSession([fake_owner, 50])  # đã đủ max_documents=50
    client, queue = _make_client(monkeypatch, session, blob_dir)

    response = client.post(
        "/api/v1/documents",
        files={"file": ("HopDong.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "QUOTA_EXCEEDED"
    assert queue.enqueued == []


def test_duplicate_name_reject_mode_returns_409(
    monkeypatch: pytest.MonkeyPatch, fake_owner: AppUser, blob_dir: Path
) -> None:
    session = _SequentialSession([fake_owner, 0, "HopDong.pdf"])  # tên đã tồn tại
    client, queue = _make_client(monkeypatch, session, blob_dir)

    response = client.post(
        "/api/v1/documents",
        files={"file": ("HopDong.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "DUPLICATE_NAME"
    assert queue.enqueued == []


def test_file_too_large_by_content_length_header_returns_413(
    monkeypatch: pytest.MonkeyPatch, fake_owner: AppUser, blob_dir: Path
) -> None:
    session = _SequentialSession([])
    client, _queue = _make_client(monkeypatch, session, blob_dir)

    response = client.post(
        "/api/v1/documents",
        files={"file": ("big.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")},
        headers={"Content-Length": str(21 * 1024 * 1024)},
    )

    assert response.status_code == 413
    assert response.json()["code"] == "FILE_TOO_LARGE"
