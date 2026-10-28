"""Task Celery cho dọn dẹp dữ liệu hết hạn (SADD §2.2.4, US-021). Chỉ
gọi use case trong `app.modules.retention.service`.
"""

import asyncio
import logging
from uuid import UUID

from app.core.db import worker_session_scope
from app.modules.analytics.service import record_event
from app.modules.retention.service import purge_expired_use_case
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _emit_deleted_events(owner_ids: list[UUID]) -> None:
    async with worker_session_scope() as session:
        for owner_id in owner_ids:
            await record_event(
                session, "document_deleted", user_id=owner_id, props={"trigger": "retention"}
            )
        await session.commit()


@celery_app.task(name="retention.purge_expired")  # type: ignore[untyped-decorator]
def purge_expired() -> int:
    """Lịch chạy 02:00 hằng ngày (T-207 khai báo trong Celery beat)."""
    owner_ids = purge_expired_use_case(batch_size=100)
    if owner_ids:
        asyncio.run(_emit_deleted_events(owner_ids))
    logger.info("retention.purge_expired đã xóa %d tài liệu hết hạn", len(owner_ids))
    return len(owner_ids)
