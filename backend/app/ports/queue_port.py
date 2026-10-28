"""`QueuePort` — cổng mà `modules/*` dùng để đẩy job nền, không import
Celery trực tiếp (nguyên tắc P-01, SADD §1.2). Adapter hiện thực hóa:
`app.adapters.celery_queue.CeleryQueueAdapter` (T-006 §5 bước 2).
"""

from typing import Any, Protocol


class QueuePort(Protocol):
    def enqueue(self, task_name: str, payload: dict[str, Any]) -> str:
        """Đẩy một job vào hàng đợi, trả về id job (để log/trace).

        `task_name` phải khớp tên task đã đăng ký trong
        `app.workers.*_tasks` (ví dụ "ingestion.process").
        """
        ...
