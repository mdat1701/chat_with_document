"""`/healthz` (liveness) và `/readyz` (readiness) — T-008 §5 bước 5-6.

`/healthz` KHÔNG chạm phụ thuộc nào (chỉ xác nhận tiến trình sống).
`/readyz` kiểm tra PostgreSQL, Redis, TEI song song, tổng timeout ≤ 2s.
"""

from __future__ import annotations

import asyncio

import httpx
import sqlalchemy as sa
from fastapi import APIRouter, Response

from app.core.config import get_settings
from app.core.db import get_engine
from app.core.redis_client import get_redis

router = APIRouter()

READYZ_TOTAL_TIMEOUT_S = 2.0


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


async def _check_postgres() -> str:
    try:
        async with get_engine().connect() as conn:
            await conn.execute(sa.text("SELECT 1"))
        return "ok"
    except Exception:  # noqa: BLE001 — readiness check, không rò rỉ chi tiết lỗi
        return "unreachable"


async def _check_redis() -> str:
    try:
        pong = await get_redis().ping()
        return "ok" if pong else "unreachable"
    except Exception:  # noqa: BLE001
        return "unreachable"


async def _check_tei() -> str:
    try:
        url = get_settings().tei_embed_url.rstrip("/") + "/health"
        async with httpx.AsyncClient(timeout=READYZ_TOTAL_TIMEOUT_S) as client:
            resp = await client.get(url)
        return "ok" if resp.status_code == 200 else "unreachable"
    except Exception:  # noqa: BLE001
        return "unreachable"


@router.get("/readyz")
async def readyz(response: Response) -> dict[str, object]:
    try:
        postgres, redis_status, tei = await asyncio.wait_for(
            asyncio.gather(_check_postgres(), _check_redis(), _check_tei()),
            timeout=READYZ_TOTAL_TIMEOUT_S,
        )
    except TimeoutError:
        postgres, redis_status, tei = "unreachable", "unreachable", "unreachable"

    checks = {"postgres": postgres, "redis": redis_status, "tei": tei}
    all_ok = all(v == "ok" for v in checks.values())
    response.status_code = 200 if all_ok else 503
    return {"status": "ok" if all_ok else "not_ready", "checks": checks}
