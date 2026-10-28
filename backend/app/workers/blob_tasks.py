"""Task Celery dọn object mồ côi trong kho tệp (SADD §2.2.4). Chỉ gọi
use case trong `app.modules.documents.service`.
"""

import logging

from app.modules.documents.service import reconcile_orphan_blobs_use_case
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="blob.reconcile_orphans")  # type: ignore[untyped-decorator]
def reconcile_orphans() -> int:
    """Lịch chạy 03:00 hằng ngày (T-207 khai báo trong Celery beat)."""
    removed = reconcile_orphan_blobs_use_case(older_than_hours=24)
    logger.info("blob.reconcile_orphans đã xóa %d object mồ côi", removed)
    return removed
