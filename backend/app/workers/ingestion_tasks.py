"""Task Celery cho pipeline ingestion (SADD §2.2.2). Chỉ gọi use case
trong `app.modules.ingestion.service` — không chứa logic PDF ở đây
(quy tắc "`workers/` là adapter vào", SADD §2.2.1, kiểm tra tự động
bằng import-linter trong `pyproject.toml`).
"""

import logging

from app.modules.ingestion.service import process_document_use_case
from app.modules.retention.service import reap_stuck_ingestion_use_case
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="ingestion.process", bind=True, max_retries=3)  # type: ignore[untyped-decorator]
def process_document(self, document_id: str) -> None:  # type: ignore[no-untyped-def]
    # Chỉ log document_id — KHÔNG log tên tệp hay nội dung (P-03).
    logger.info("ingestion.process nhận document_id=%s", document_id)
    process_document_use_case(document_id)


@celery_app.task(name="maintenance.reap_stuck")  # type: ignore[untyped-decorator]
def reap_stuck() -> int:
    """Lịch chạy mỗi 5 phút (T-207 khai báo trong Celery beat)."""
    return reap_stuck_ingestion_use_case(stuck_after_minutes=10)
