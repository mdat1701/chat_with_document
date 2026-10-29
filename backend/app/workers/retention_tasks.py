"""Task Celery cho dọn dẹp dữ liệu hết hạn (SADD §2.2.4, US-021). Chỉ
gọi use case trong `app.modules.retention.service`.
"""

import asyncio
import logging
from datetime import UTC, datetime

from app.core.db import worker_session_scope
from app.core.models import AuditLog
from app.modules.analytics.service import record_event
from app.modules.retention.service import DeletedDocument, _purge_expired
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


async def _purge_and_emit(batch_size: int) -> list[DeletedDocument]:
    """Gộp `_purge_expired()` + `_emit_deleted_events()` vào CHUNG một
    `asyncio.run()` — xem ghi chú chi tiết ở
    `app/workers/ingestion_tasks.py::_run_pipeline_and_emit` (2 lệnh
    `asyncio.run()` tách rời cùng dùng một `AsyncEngine` singleton vỡ
    ngay ở event loop thứ hai trên asyncpg — chỉ lộ ra khi chạy worker
    thật trên Postgres thật, không unit test mock DB nào bắt được)."""
    deleted = await _purge_expired(batch_size)
    if deleted:
        await _emit_deleted_events(deleted)
    return deleted


@celery_app.task(name="retention.purge_expired")  # type: ignore[untyped-decorator]
def purge_expired() -> int:
    """Lịch chạy 02:00 hằng ngày (T-207 khai báo trong Celery beat)."""
    deleted = asyncio.run(_purge_and_emit(batch_size=100))
    logger.info("retention.purge_expired đã xóa %d tài liệu hết hạn", len(deleted))
    return len(deleted)
