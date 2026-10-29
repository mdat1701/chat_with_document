"""Small Redis-backed fixed-window limiter shared by upload and Q&A APIs."""

import logging
from dataclasses import dataclass

from redis.asyncio import Redis

from app.core.metrics import ratelimit_rejected_total, ratelimit_unavailable_total

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after_seconds: int


async def check_rate_limit(
    redis: Redis, *, key: str, limit: int, window_seconds: int, scope: str = "unknown"
) -> RateLimitResult:
    try:
        count = int(await redis.incr(key))
        if count == 1:
            await redis.expire(key, window_seconds)
        ttl = await redis.ttl(key)
        result = RateLimitResult(count <= limit, max(1, int(ttl)))
    except Exception:
        # Pilot behavior is fail-open (ngược với RLS ở T-104 vốn fail
        # closed) — nhưng phải quan sát được, không được nuốt lỗi im lặng.
        logger.warning("check_rate_limit fail-open: Redis unavailable (scope=%s)", scope)
        ratelimit_unavailable_total.inc()
        return RateLimitResult(True, 0)
    if not result.allowed:
        ratelimit_rejected_total.labels(scope=scope).inc()
    return result
