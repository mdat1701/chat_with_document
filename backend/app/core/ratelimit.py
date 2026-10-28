"""Small Redis-backed fixed-window limiter shared by upload and Q&A APIs."""

from dataclasses import dataclass

from redis.asyncio import Redis


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after_seconds: int


async def check_rate_limit(
    redis: Redis, *, key: str, limit: int, window_seconds: int
) -> RateLimitResult:
    try:
        count = int(await redis.incr(key))
        if count == 1:
            await redis.expire(key, window_seconds)
        ttl = await redis.ttl(key)
        return RateLimitResult(count <= limit, max(1, int(ttl)))
    except Exception:
        # Pilot behavior is fail-open; callers can log/measure the outage.
        return RateLimitResult(True, 0)
