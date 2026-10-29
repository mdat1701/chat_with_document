"""Kiểm thử allow-list sự kiện/thuộc tính và hash một chiều `user_id`
(T-404/T-503 AC-020.1) — trước phiên này `app/modules/analytics` không
có test tự động nào."""

from __future__ import annotations

import hashlib
import hmac
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.modules.analytics import service


class _FakeSettings:
    analytics_hash_secret = "test-secret"
    service_name = "cwd-backend-test"
    app_version = "9.9.9-test"


@pytest.fixture(autouse=True)
def _patch_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service, "get_settings", lambda: _FakeSettings())


async def test_unknown_event_name_is_rejected_and_not_added() -> None:
    session = MagicMock()

    await service.record_event(session, "not_a_real_event")

    session.add.assert_not_called()


async def test_unknown_props_are_dropped_but_event_still_recorded() -> None:
    session = MagicMock()

    await service.record_event(
        session,
        "question_submitted",
        props={"question_length": 10, "question_text": "nội dung không được phép"},
    )

    session.add.assert_called_once()
    event = session.add.call_args.args[0]
    assert event.props == {"question_length": 10}
    assert "question_text" not in event.props


async def test_user_id_is_hashed_not_stored_raw() -> None:
    session = MagicMock()
    user_id = uuid4()

    await service.record_event(session, "session_started", user_id=user_id)

    event = session.add.call_args.args[0]
    expected = hmac.new(
        b"test-secret", str(user_id).encode(), hashlib.sha256
    ).hexdigest()
    assert event.user_hash == expected
    assert str(user_id) not in str(event.user_hash)


async def test_no_user_id_means_no_hash() -> None:
    session = MagicMock()

    await service.record_event(session, "session_started")

    event = session.add.call_args.args[0]
    assert event.user_hash is None


async def test_sid_is_hashed_not_stored_raw() -> None:
    session = MagicMock()
    raw_sid = "cwd_sid_raw_token_value"

    await service.record_event(session, "session_started", sid=raw_sid)

    event = session.add.call_args.args[0]
    expected = hmac.new(b"test-secret", raw_sid.encode(), hashlib.sha256).hexdigest()
    assert event.session_id == expected
    assert raw_sid not in str(event.session_id)


async def test_no_sid_means_no_session_id() -> None:
    session = MagicMock()

    await service.record_event(session, "session_started")

    event = session.add.call_args.args[0]
    assert event.session_id is None


async def test_app_version_read_from_settings_not_service_name() -> None:
    session = MagicMock()

    await service.record_event(session, "session_started")

    event = session.add.call_args.args[0]
    assert event.app_version == "9.9.9-test"


async def test_allowed_event_names_cover_minimum_funnel() -> None:
    required = {
        "session_started", "document_upload_started", "document_processing_succeeded",
        "document_processing_failed", "document_deleted", "question_submitted",
        "answer_rendered", "citation_viewed",
    }
    assert required.issubset(service.ALLOWED_EVENTS)
