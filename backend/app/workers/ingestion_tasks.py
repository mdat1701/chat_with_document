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
    _publish_status,
    _set_failed,
    process_document_use_case,
)
from app.modules.retention.service import reap_stuck_ingestion_use_case
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


@celery_app.task(name="ingestion.process", bind=True, max_retries=3)  # type: ignore[untyped-decorator]
def process_document(self, document_id: str) -> None:  # type: ignore[no-untyped-def]
    # Chỉ log document_id — KHÔNG log tên tệp hay nội dung (P-03).
    logger.info("ingestion.process nhận document_id=%s", document_id)
    try:
        process_document_use_case(document_id, TeiEmbeddingAdapter())
    except InfrastructureError as exc:
        try:
            raise self.retry(exc=exc, countdown=2 ** (self.request.retries + 1))
        except self.MaxRetriesExceededError:
            asyncio.run(_set_failed(UUID(document_id), "INGESTION_FAILED"))
    asyncio.run(_emit_processing_outcome_event(document_id))


async def _publish_reaped_status(document_ids: list[UUID]) -> None:
    for document_id in document_ids:
        documents_failed_total.labels(error_code="INGESTION_FAILED").inc()
        await _publish_status(document_id, "failed", "INGESTION_FAILED", None)


@celery_app.task(name="maintenance.reap_stuck")  # type: ignore[untyped-decorator]
def reap_stuck() -> int:
    """Lịch chạy mỗi 5 phút (T-207 khai báo trong Celery beat)."""
    reaped_ids = reap_stuck_ingestion_use_case(stuck_after_minutes=10)
    if reaped_ids:
        # T-204 §5 bước 1: worker phải publish sau MỌI lần đổi
        # document.status, kể cả nhánh job bị treo quá hạn — trước đây
        # `_reap_stuck` chỉ đổi DB, không có sự kiện SSE nào, nên UI phải
        # tự làm mới trang mới thấy tài liệu chuyển sang "Lỗi".
        asyncio.run(_publish_reaped_status(reaped_ids))
    return len(reaped_ids)
