"""Task Celery cho dọn dẹp dữ liệu hết hạn (SADD §2.2.4, US-021). Chỉ
gọi use case trong `app.modules.retention.service`.
"""

import asyncio
import logging
from datetime import UTC, datetime

from app.core.db import worker_session_scope
from app.core.models import AuditLog
from app.modules.analytics.service import record_event
from app.modules.retention.service import DeletedDocument, purge_expired_use_case
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _emit_deleted_events(deleted: list[DeletedDocument]) -> None:
    async with worker_session_scope() as session:
        for item in deleted:
            session.add(
                AuditLog(
                    ts=datetime.now(UTC),
                    actor_id=None,  # xóa tự động bởi retention, không phải người dùng
                    action="document_deleted",
                    target_type="document",
                    target_id=str(item.document_id),
                    outcome="ok",
                )
            )
            await record_event(
                session,
                "document_deleted",
                user_id=item.owner_id,
                props={"trigger": "retention"},
            )
        await session.commit()


@celery_app.task(name="retention.purge_expired")  # type: ignore[untyped-decorator]
def purge_expired() -> int:
    """Lịch chạy 02:00 hằng ngày (T-207 khai báo trong Celery beat)."""
    deleted = purge_expired_use_case(batch_size=100)
    if deleted:
        asyncio.run(_emit_deleted_events(deleted))
    logger.info("retention.purge_expired đã xóa %d tài liệu hết hạn", len(deleted))
    return len(deleted)
