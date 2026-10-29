"""Task Celery cho pipeline ingestion (SADD §2.2.2). Chỉ gọi use case
trong `app.modules.ingestion.service` — không chứa logic PDF ở đây
(quy tắc "`workers/` là adapter vào", SADD §2.2.1, kiểm tra tự động
bằng import-linter trong `pyproject.toml`).
"""

import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.adapters.tei_embedding import TeiEmbeddingAdapter
from app.core.db import worker_session_scope
from app.core.metrics import documents_failed_total
from app.modules.analytics.service import record_event
from app.modules.documents.models import Document
from app.modules.ingestion.service import (
    InfrastructureError,
    _process_document,
    _publish_status,
    _set_failed,
)
from app.modules.retention.service import _reap_stuck
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _emit_processing_outcome_event(document_id: str) -> None:
    """T-404: phát `document_processing_succeeded`/`_failed` sau khi
    pipeline ingestion kết thúc — chỉ chỉ số (trang, thời lượng, mã lỗi),
    KHÔNG tên tệp/nội dung (P-03)."""
    async with worker_session_scope() as session:
        document = (
            await session.execute(select(Document).where(Document.id == UUID(document_id)))
        ).scalar_one_or_none()
        if document is None or document.status not in {"ready", "failed"}:
            return
        duration_ms = int((datetime.now(UTC) - document.uploaded_at).total_seconds() * 1000)
        if document.status == "ready":
            await record_event(
                session,
                "document_processing_succeeded",
                user_id=document.owner_id,
                props={"page_count": document.page_count, "duration_ms": duration_ms},
            )
        else:
            await record_event(
                session,
                "document_processing_failed",
                user_id=document.owner_id,
                props={"error_code": document.error_code},
            )
        await session.commit()


async def _run_pipeline_and_emit(task: object, document_id: str) -> None:
    """Gộp `_process_document()` + `_emit_processing_outcome_event()` vào
    CHUNG một `asyncio.run()` (xem `process_document` bên dưới) — trước
    đây là 2 lệnh `asyncio.run()` tách rời, cả hai cùng dùng chung một
    `AsyncEngine` singleton (`get_worker_engine()`, T-005). asyncpg buộc
    một connection phải dùng lại TRONG CHÍNH event loop đã tạo ra nó;
    `asyncio.run()` thứ hai mở một event loop MỚI rồi lấy lại connection
    đã pool từ event loop thứ nhất (đã đóng) — vỡ ngay ở bước
    `pool_pre_ping`, lỗi `AttributeError: 'NoneType' object has no
    attribute 'send'` (transport của event loop cũ đã mất). Hậu quả
    thật: MỌI lần xử lý tài liệu thành công vẫn bị Celery ghi nhận là
    task lỗi/thử lại ngay ở bước phát sự kiện phân tích cuối cùng — dù
    tài liệu đã thật sự chuyển sang `ready` đúng. Lỗi chỉ lộ ra khi chạy
    worker thật trên Postgres thật (phát hiện khi chạy TC-004 thủ công
    bằng cách gọi thẳng `process_document.run()` thay vì qua Celery)."""
    try:
        await _process_document(UUID(document_id), TeiEmbeddingAdapter())
    except InfrastructureError as exc:
        try:
            # T-201 §3: backoff 2s/8s/32s (tương đương retry_backoff=2,
            # retry_backoff_max=32 của Celery) — trước đây dùng
            # 2**(retries+1) cho ra 2s/4s/8s, lệch với spec.
            raise task.retry(exc=exc, countdown=2 * 4**task.request.retries)  # type: ignore[attr-defined]
        except task.MaxRetriesExceededError:  # type: ignore[attr-defined]
            await _set_failed(UUID(document_id), "INGESTION_FAILED")
    await _emit_processing_outcome_event(document_id)


@celery_app.task(name="ingestion.process", bind=True, max_retries=3)  # type: ignore[untyped-decorator]
def process_document(self, document_id: str) -> None:  # type: ignore[no-untyped-def]
    # Chỉ log document_id — KHÔNG log tên tệp hay nội dung (P-03).
    logger.info("ingestion.process nhận document_id=%s", document_id)
    asyncio.run(_run_pipeline_and_emit(self, document_id))


async def _publish_reaped_status(document_ids: list[UUID]) -> None:
    for document_id in document_ids:
        documents_failed_total.labels(error_code="INGESTION_FAILED").inc()
        await _publish_status(document_id, "failed", "INGESTION_FAILED", None)


async def _reap_and_publish(stuck_after_minutes: int) -> list[UUID]:
    """Gộp `_reap_stuck()` + `_publish_reaped_status()` vào CHUNG một
    `asyncio.run()` — xem ghi chú ở `_run_pipeline_and_emit` phía trên
    (2 lệnh `asyncio.run()` tách rời dùng chung một `AsyncEngine`
    singleton vỡ ngay ở event loop thứ hai trên asyncpg)."""
    reaped_ids = await _reap_stuck(stuck_after_minutes)
    if reaped_ids:
        # T-204 §5 bước 1: worker phải publish sau MỌI lần đổi
        # document.status, kể cả nhánh job bị treo quá hạn — trước đây
        # `_reap_stuck` chỉ đổi DB, không có sự kiện SSE nào, nên UI phải
        # tự làm mới trang mới thấy tài liệu chuyển sang "Lỗi".
        await _publish_reaped_status(reaped_ids)
    return reaped_ids


@celery_app.task(name="maintenance.reap_stuck")  # type: ignore[untyped-decorator]
def reap_stuck() -> int:
    """Lịch chạy mỗi 5 phút (T-207 khai báo trong Celery beat)."""
    reaped_ids = asyncio.run(_reap_and_publish(stuck_after_minutes=10))
    return len(reaped_ids)
