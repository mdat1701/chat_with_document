"""Cấu hình Celery dùng chung cho `worker` và `beat` (SADD §2.2.4,
§4.2.2, §4.2.3). Lịch job định kỳ thật (retention, reap_stuck,
blob reconcile) khai báo ở T-207.
"""

from celery import Celery

from app.core.config import get_settings

celery_app = Celery(
    "cwd",
    broker=get_settings().celery_broker_url,
    backend=None,
    # Mỗi module task mới (T-201, T-207, ...) phải thêm vào đây để được
    # đăng ký khi `celery -A app.workers.celery_app worker` khởi động.
    include=[
        "app.workers.ping_tasks",
        "app.workers.ingestion_tasks",
        "app.workers.retention_tasks",
        "app.workers.blob_tasks",
    ],
)

celery_app.conf.update(
    task_acks_late=True,  # SADD §4.2.2 — job trả lại hàng đợi nếu pod chết
    worker_prefetch_multiplier=1,  # task nặng, không gom trước
    task_reject_on_worker_lost=True,
    task_default_queue="maintenance",
    task_routes={
        "ingestion.*": {"queue": "ingestion"},
        "retention.*": {"queue": "maintenance"},
        "blob.*": {"queue": "maintenance"},
        "maintenance.*": {"queue": "maintenance"},
    },
    task_time_limit=15 * 60,  # chặn job treo vĩnh viễn
    task_soft_time_limit=10 * 60,  # khớp ngưỡng reap_stuck (T-207)
    timezone="Asia/Ho_Chi_Minh",
)
