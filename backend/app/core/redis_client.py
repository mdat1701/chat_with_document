"""Client Redis dùng chung cho `api` (phiên, rate limit, pub/sub —
T-101/T-105/T-204). KHÔNG dùng cho broker Celery (xem
`celery_broker_url`, DB Redis riêng theo SADD §2.3)."""

from functools import lru_cache

import redis.asyncio as redis

from app.core.config import get_settings


@lru_cache
def get_redis() -> redis.Redis:
    return redis.from_url(get_settings().redis_url, decode_responses=True)  # type: ignore[no-untyped-call,no-any-return]
