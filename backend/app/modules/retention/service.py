"""Đánh dấu tài liệu sắp hết hạn, xóa cứng tài liệu quá
DF-05 (90 ngày) và dữ liệu phát sinh của nó.

Story: US-021.
"""


def purge_expired_use_case(batch_size: int = 100) -> int:
    """Điểm vào mà `app.workers.retention_tasks.purge_expired` gọi
    (T-006). Trả về số tài liệu đã xóa. Logic thật ở T-207."""
    raise NotImplementedError("Cài đặt ở T-207")


def reap_stuck_ingestion_use_case(stuck_after_minutes: int = 10) -> int:
    """Điểm vào mà `app.workers.ingestion_tasks.reap_stuck` gọi
    (T-006). Trả về số job bị chuyển sang `failed`. Logic thật ở T-207."""
    raise NotImplementedError("Cài đặt ở T-207")
