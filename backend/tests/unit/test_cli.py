"""Kiểm thử `app.cli` (T-103) — trước phiên này không có test tự động
nào cho module này (chỉ `test_architecture_boundaries.py` xác nhận ranh
giới import, không xác nhận hành vi CLI). Dùng factory DB giả lập
(async context manager tối giản) thay vì Postgres thật."""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app import cli


def test_validate_rejects_bad_email() -> None:
    with pytest.raises(ValueError, match="Email không hợp lệ"):
        cli._validate("khong-phai-email", "user")


def test_validate_rejects_unknown_role() -> None:
    with pytest.raises(ValueError, match="Role không hợp lệ"):
        cli._validate("u@example.com", "superadmin")


def test_validate_accepts_known_good_input() -> None:
    cli._validate("u@example.com", "user")  # không ném lỗi


def test_read_access_file_parses_yaml_like_list(tmp_path: Path) -> None:
    path = tmp_path / "access.yaml"
    path.write_text(
        "- email: a@example.com\n  role: user\n- email: b@example.com\n  role: admin\n",
        encoding="utf-8",
    )

    entries = cli._read_access_file(str(path))

    assert entries == [("a@example.com", "user"), ("b@example.com", "admin")]


def test_read_access_file_defaults_role_to_user(tmp_path: Path) -> None:
    path = tmp_path / "access.yaml"
    path.write_text("- email: a@example.com\n", encoding="utf-8")

    entries = cli._read_access_file(str(path))

    assert entries == [("a@example.com", "user")]


def test_read_access_file_rejects_invalid_email(tmp_path: Path) -> None:
    path = tmp_path / "access.yaml"
    path.write_text("- email: khong-hop-le\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Email không hợp lệ"):
        cli._read_access_file(str(path))


class _FakeResult:
    def __init__(self, value: Any) -> None:
        self._value = value

    def scalar_one_or_none(self) -> Any:
        return self._value

    def scalars(self) -> _FakeResult:
        return self

    def all(self) -> Any:
        return self._value


class _FakeBegin:
    async def __aenter__(self) -> _FakeBegin:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        return None


class _FakeSession:
    def __init__(self, execute_results: list[Any], get_results: list[Any] | None = None) -> None:
        self._execute_results = list(execute_results)
        self._get_results = list(get_results or [])
        self.added: list[object] = []
        self.add = MagicMock(side_effect=self.added.append)
        self.flush = AsyncMock()

    def begin(self) -> _FakeBegin:
        return _FakeBegin()

    async def execute(self, _statement: object) -> _FakeResult:
        return _FakeResult(self._execute_results.pop(0))

    async def get(self, _model: object, _pk: object) -> Any:
        return self._get_results.pop(0) if self._get_results else None


class _FakeSessionCtx:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    async def __aenter__(self) -> _FakeSession:
        return self._session

    async def __aexit__(self, *_exc: object) -> None:
        return None


def _patch_session(monkeypatch: pytest.MonkeyPatch, session: _FakeSession) -> None:
    monkeypatch.setattr(cli, "get_session_factory", lambda: lambda: _FakeSessionCtx(session))
    monkeypatch.setattr(cli, "_actor_id", lambda: None)


async def test_grant_access_creates_new_active_user_and_audit_log(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    session = _FakeSession(execute_results=[None], get_results=[None])
    _patch_session(monkeypatch, session)

    code = await cli.grant_access("new@example.com", "user")

    assert code == 0
    assert "Đã cấp quyền" in capsys.readouterr().out
    # 1 AppUser mới + 1 UserRole mới + 1 AuditLog = 3 lời gọi add().
    assert len(session.added) == 3
    audit_entries = [item for item in session.added if type(item).__name__ == "AuditLog"]
    assert audit_entries and audit_entries[0].action == "access_granted"


async def test_grant_access_is_idempotent_for_existing_active_user_with_role(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    existing_user = MagicMock()
    existing_user.id = uuid.uuid4()
    existing_user.active = True
    session = _FakeSession(execute_results=[existing_user], get_results=[object()])
    _patch_session(monkeypatch, session)

    code = await cli.grant_access("existing@example.com", "user")

    assert code == 0
    assert "Không thay đổi" in capsys.readouterr().out
    # Không tạo AppUser/UserRole mới, chỉ ghi AuditLog.
    assert len(session.added) == 1


async def test_revoke_access_without_yes_flag_exits_1_and_changes_nothing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    session = _FakeSession(execute_results=[])
    _patch_session(monkeypatch, session)

    code = await cli.revoke_access("u@example.com", confirmed=False)

    assert code == 1
    assert "--yes" in capsys.readouterr().err
    assert session.added == []


async def test_revoke_access_deletes_all_sessions_immediately(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    user = MagicMock()
    user.id = uuid.uuid4()
    session = _FakeSession(execute_results=[user])
    _patch_session(monkeypatch, session)
    revoke_calls: list[str] = []

    async def _fake_delete_all(_redis: object, user_id: str) -> int:
        revoke_calls.append(user_id)
        return 1

    monkeypatch.setattr(cli, "delete_all_sessions_for_user", _fake_delete_all)
    monkeypatch.setattr(cli, "get_redis", lambda: object())

    code = await cli.revoke_access("u@example.com", confirmed=True)

    assert code == 0
    assert revoke_calls == [str(user.id)]
    assert user.active is False
    assert isinstance(user.revoked_at, datetime)
    audit_entries = [item for item in session.added if type(item).__name__ == "AuditLog"]
    assert audit_entries[0].action == "access_revoked"


async def test_revoke_access_unknown_email_exits_1(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    session = _FakeSession(execute_results=[None])
    _patch_session(monkeypatch, session)

    code = await cli.revoke_access("khong-ton-tai@example.com", confirmed=True)

    assert code == 1
    assert "Không tìm thấy" in capsys.readouterr().err
