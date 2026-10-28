"""Kiểm thử quản lý phiên (T-101 §7) bằng `fakeredis` — giao thức
Redis thật trong bộ nhớ, không mock thủ công từng lệnh."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest
from fakeredis import FakeAsyncRedis

from app.modules.identity import sessions


@pytest.fixture
async def redis() -> FakeAsyncRedis:
    client = FakeAsyncRedis()
    yield client
    await client.aclose()


async def test_create_then_get_session_round_trips(redis: FakeAsyncRedis) -> None:
    sid, data = await sessions.create_session(redis, user_id="u1", roles=["user"])
    fetched = await sessions.get_session(redis, sid)
    assert fetched is not None
    assert fetched.user_id == "u1"
    assert fetched.roles == ["user"]
    assert fetched.csrf_token == data.csrf_token


async def test_unknown_sid_returns_none(redis: FakeAsyncRedis) -> None:
    assert await sessions.get_session(redis, "khong-ton-tai") is None


async def test_absolute_12h_expiry_overrides_sliding_ttl(redis: FakeAsyncRedis) -> None:
    """Dù Redis TTL trượt chưa hết, phiên tạo cách đây > 12 giờ vẫn phải
    coi là hết hạn (T-101 kiểm thử bắt buộc: "Session tạo cách đây 12
    giờ 1 phút nhưng vừa hoạt động → vẫn hết hạn")."""
    sid, _ = await sessions.create_session(redis, user_id="u1", roles=["user"])

    twelve_hours_one_minute_ago = time.time() - (12 * 3600 + 60)
    with patch("app.modules.identity.sessions.time.time", return_value=twelve_hours_one_minute_ago):
        # created_at ghi tại thời điểm "quá khứ" giả lập — mô phỏng phiên cũ.
        sid2, _ = await sessions.create_session(redis, user_id="u2", roles=["user"])

    assert await sessions.get_session(redis, sid) is not None  # phiên mới vẫn còn
    assert await sessions.get_session(redis, sid2) is None  # phiên "12h1'" đã hết hạn


async def test_touch_session_updates_last_seen_and_keeps_created_at(redis: FakeAsyncRedis) -> None:
    sid, original = await sessions.create_session(redis, user_id="u1", roles=["user"])
    await sessions.touch_session(redis, sid, original)
    touched = await sessions.get_session(redis, sid)
    assert touched is not None
    assert touched.created_at == original.created_at
    assert touched.last_seen_at >= original.last_seen_at


async def test_delete_session_removes_key_and_user_index(redis: FakeAsyncRedis) -> None:
    sid, _ = await sessions.create_session(redis, user_id="u1", roles=["user"])
    await sessions.delete_session(redis, sid, user_id="u1")
    assert await sessions.get_session(redis, sid) is None
    assert await redis.smembers(sessions._user_sessions_key("u1")) == set()  # type: ignore[comparison-overlap]


async def test_delete_all_sessions_for_user_revokes_every_session_immediately(
    redis: FakeAsyncRedis,
) -> None:
    """AC-023.2: thu hồi quyền phải xóa MỌI phiên của người dùng đó."""
    sid1, _ = await sessions.create_session(redis, user_id="u1", roles=["user"])
    sid2, _ = await sessions.create_session(redis, user_id="u1", roles=["user"])
    other_sid, _ = await sessions.create_session(redis, user_id="u-khac", roles=["user"])

    removed = await sessions.delete_all_sessions_for_user(redis, "u1")

    assert removed == 2
    assert await sessions.get_session(redis, sid1) is None
    assert await sessions.get_session(redis, sid2) is None
    assert await sessions.get_session(redis, other_sid) is not None  # không đụng người khác


async def test_delete_all_sessions_for_user_with_no_sessions_returns_zero(
    redis: FakeAsyncRedis,
) -> None:
    assert await sessions.delete_all_sessions_for_user(redis, "chua-tung-dang-nhap") == 0
