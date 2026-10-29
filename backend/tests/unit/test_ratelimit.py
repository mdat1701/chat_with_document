"""Kiểm thử `check_rate_limit` (T-105) bằng `fakeredis` — trước phiên
này không có test tự động nào cho tiện ích này."""

from __future__ import annotations

import pytest
from fakeredis import FakeAsyncRedis

from app.core.metrics import ratelimit_rejected_total, ratelimit_unavailable_total
from app.core.ratelimit import check_rate_limit


@pytest.fixture
async def redis() -> FakeAsyncRedis:
    client = FakeAsyncRedis()
    yield client
    await client.aclose()


async def test_allows_requests_under_the_limit(redis: FakeAsyncRedis) -> None:
    for _ in range(5):
        result = await check_rate_limit(redis, key="rl:test", limit=5, window_seconds=60)
        assert result.allowed is True


async def test_blocks_the_request_that_exceeds_the_limit(redis: FakeAsyncRedis) -> None:
    for _ in range(5):
        await check_rate_limit(redis, key="rl:test", limit=5, window_seconds=60)

    sixth = await check_rate_limit(redis, key="rl:test", limit=5, window_seconds=60)

    assert sixth.allowed is False
    assert sixth.retry_after_seconds >= 1


async def test_different_keys_are_independent(redis: FakeAsyncRedis) -> None:
    for _ in range(5):
        await check_rate_limit(redis, key="rl:user-a", limit=5, window_seconds=60)

    result_for_b = await check_rate_limit(redis, key="rl:user-b", limit=5, window_seconds=60)

    assert result_for_b.allowed is True


async def test_fails_open_when_redis_is_unavailable() -> None:
    class _BrokenRedis:
        async def incr(self, _key: str) -> int:
            raise ConnectionError("Redis down")

    before = ratelimit_unavailable_total._value.get()  # type: ignore[attr-defined]

    result = await check_rate_limit(_BrokenRedis(), key="rl:test", limit=1, window_seconds=60)  # type: ignore[arg-type]

    assert result.allowed is True
    # T-105: fail-open phải quan sát được, không được nuốt lỗi im lặng.
    assert ratelimit_unavailable_total._value.get() == before + 1  # type: ignore[attr-defined]


async def test_increments_rejected_metric_with_scope_label(redis: FakeAsyncRedis) -> None:
    before = ratelimit_rejected_total.labels(scope="upload")._value.get()  # type: ignore[attr-defined]
    for _ in range(5):
        await check_rate_limit(redis, key="rl:scoped", limit=5, window_seconds=60, scope="upload")

    sixth = await check_rate_limit(
        redis, key="rl:scoped", limit=5, window_seconds=60, scope="upload"
    )

    assert sixth.allowed is False
    assert ratelimit_rejected_total.labels(scope="upload")._value.get() == before + 1  # type: ignore[attr-defined]
