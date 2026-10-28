"""Quản lý phiên trong Redis (T-101 §4, §5 bước 6-7).

`session:{sid}` TTL trượt 2 giờ theo hoạt động gần nhất, nhưng KHÔNG
BAO GIỜ vượt quá 12 giờ tuyệt đối tính từ lúc tạo — đây là lý do field
`created_at` được lưu riêng, không chỉ dựa vào TTL của Redis.
`sessions_by_user:{user_id}` cho phép T-103 thu hồi toàn bộ phiên của
một người dùng ngay lập tức.
"""

from __future__ import annotations

import json
import secrets
import time
from dataclasses import asdict, dataclass

from redis.asyncio import Redis

SLIDING_TTL_SECONDS = 2 * 60 * 60
ABSOLUTE_MAX_SECONDS = 12 * 60 * 60


@dataclass(frozen=True)
class SessionData:
    user_id: str
    csrf_token: str
    roles: list[str]
    created_at: float
    last_seen_at: float


def _session_key(sid: str) -> str:
    return f"session:{sid}"


def _user_sessions_key(user_id: str) -> str:
    return f"sessions_by_user:{user_id}"


async def create_session(
    redis: Redis, *, user_id: str, roles: list[str]
) -> tuple[str, SessionData]:
    sid = secrets.token_urlsafe(32)
    now = time.time()
    data = SessionData(
        user_id=user_id,
        csrf_token=secrets.token_urlsafe(32),
        roles=roles,
        created_at=now,
        last_seen_at=now,
    )
    await redis.set(_session_key(sid), json.dumps(asdict(data)), ex=SLIDING_TTL_SECONDS)
    await redis.sadd(_user_sessions_key(user_id), sid)  # type: ignore[misc]
    return sid, data


async def get_session(redis: Redis, sid: str) -> SessionData | None:
    """Trả `None` nếu không có phiên, hoặc nếu đã vượt 12 giờ tuyệt đối
    (tự xóa — hành vi tương đương hết hạn thật dù Redis TTL trượt chưa
    kịp hết)."""
    raw = await redis.get(_session_key(sid))
    if raw is None:
        return None
    payload = json.loads(raw)
    data = SessionData(**payload)

    if time.time() - data.created_at > ABSOLUTE_MAX_SECONDS:
        await delete_session(redis, sid, user_id=data.user_id)
        return None

    return data


async def touch_session(redis: Redis, sid: str, data: SessionData) -> None:
    """Trượt TTL thêm `SLIDING_TTL_SECONDS` kể từ bây giờ — gọi sau mỗi
    request thành công (AC-001.3)."""
    updated = SessionData(
        user_id=data.user_id,
        csrf_token=data.csrf_token,
        roles=data.roles,
        created_at=data.created_at,
        last_seen_at=time.time(),
    )
    await redis.set(_session_key(sid), json.dumps(asdict(updated)), ex=SLIDING_TTL_SECONDS)


async def delete_session(redis: Redis, sid: str, *, user_id: str) -> None:
    await redis.delete(_session_key(sid))
    await redis.srem(_user_sessions_key(user_id), sid)  # type: ignore[misc]


async def delete_all_sessions_for_user(redis: Redis, user_id: str) -> int:
    """T-103 (thu hồi quyền): xóa MỌI phiên của một người dùng ngay lập
    tức, có hiệu lực ở request tiếp theo (AC-023.2)."""
    key = _user_sessions_key(user_id)
    sids = await redis.smembers(key)  # type: ignore[misc]
    if not sids:
        return 0
    pipe = redis.pipeline()
    for sid in sids:
        sid_str = sid.decode() if isinstance(sid, bytes) else sid
        pipe.delete(_session_key(sid_str))
    pipe.delete(key)
    await pipe.execute()
    return len(sids)
