"""Hiện thực hóa `QueuePort` bằng Celery (T-006 §5 bước 2). Đây là nơi
DUY NHẤT trong hệ thống gọi `celery_app.send_task` trực tiếp —
`modules/*` (ví dụ `documents` ở T-108) chỉ phụ thuộc vào `QueuePort`,
không import Celery.
"""

import importlib
from typing import Any


class _CeleryProxy:
    def send_task(self, task_name: str, *, kwargs: dict[str, Any]) -> Any:
        module = importlib.import_module("app.workers.celery_app")
        return module.celery_app.send_task(task_name, kwargs=kwargs)


celery_app = _CeleryProxy()


class CeleryQueueAdapter:
    def enqueue(self, task_name: str, payload: dict[str, Any]) -> str:
        result = celery_app.send_task(task_name, kwargs=payload)
        return str(result.id)
