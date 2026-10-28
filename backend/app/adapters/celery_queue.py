"""Hiện thực hóa `QueuePort` bằng Celery (T-006 §5 bước 2). Đây là nơi
DUY NHẤT trong hệ thống gọi `celery_app.send_task` trực tiếp —
`modules/*` (ví dụ `documents` ở T-108) chỉ phụ thuộc vào `QueuePort`,
không import Celery.
"""

from typing import Any

from app.workers.celery_app import celery_app


class CeleryQueueAdapter:
    def enqueue(self, task_name: str, payload: dict[str, Any]) -> str:
        result = celery_app.send_task(task_name, kwargs=payload)
        return str(result.id)
