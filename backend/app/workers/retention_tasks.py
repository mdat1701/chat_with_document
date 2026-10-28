"""Task Celery cho dọn dẹp dữ liệu hết hạn (SADD §2.2.4, US-021). Chỉ
gọi use case trong `app.modules.retention.service`.
"""

import logging

from app.modules.retention.service import purge_expired_use_case
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="retention.purge_expired")  # type: ignore[untyped-decorator]
def purge_expired() -> int:
    """Lịch chạy 02:00 hằng ngày (T-207 khai báo trong Celery beat)."""
    deleted = purge_expired_use_case(batch_size=100)
    logger.info("retention.purge_expired đã xóa %d tài liệu hết hạn", deleted)
    return deleted
