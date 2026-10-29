"""Cấu hình Celery dùng chung cho `worker` và `beat` (SADD §2.2.4,
§4.2.2, §4.2.3). Lịch job định kỳ thật (retention, reap_stuck,
blob reconcile) khai báo ở T-207.
"""

from celery import Celery

# Nạp đủ MỌI models.py vào cùng một registry `Base.metadata` trước khi bất
# kỳ task nào chạy — giống hệt `migrations/env.py` phải làm. Không module
# task nào (`ingestion_tasks`, `retention_tasks`, ...) tự import
# `app.modules.identity.models` (chỉ cần `Document`/`AuditLog`), nhưng cột
# `document.owner_id`/`answer.owner_id` tham chiếu `app_user.id` bằng
# CHUỖI ("app_user.id") — SQLAlchemy chỉ phân giải được chuỗi này nếu bảng
# `app_user` đã được đăng ký trong cùng registry. Thiếu dòng này, worker
# THẬT sẽ crash ngay ở lần `flush()` đầu tiên của BẤT KỲ task nào đụng tới
# bảng có FK sang `app_user` (tức gần như mọi task) với lỗi
# `NoReferencedTableError` — chỉ lộ ra khi chạy worker thật trên Postgres
# thật, không unit test nào mock DB session bắt được (phát hiện khi chạy
# TC-004 thủ công, gọi thẳng `process_document.run()`).
import app.core.models  # noqa: E402, F401
import app.modules.documents.models  # noqa: E402, F401
import app.modules.feedback.models  # noqa: E402, F401
import app.modules.identity.models  # noqa: E402, F401
import app.modules.qa.models  # noqa: E402, F401
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.tracing import configure_tracing, instrument_celery

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
    beat_schedule={
        "retention-purge-expired": {
            "task": "retention.purge_expired",
            "schedule": 24 * 60 * 60,
            "options": {"queue": "maintenance"},
        },
        "ingestion-reap-stuck": {
            "task": "maintenance.reap_stuck",
            "schedule": 5 * 60,
            "options": {"queue": "maintenance"},
        },
        "blob-reconcile-orphans": {
            "task": "blob.reconcile_orphans",
            "schedule": 24 * 60 * 60,
            "options": {"queue": "maintenance"},
        },
    },
)

# T-007: logging JSON + trace_id lan từ api sang worker qua header task
# (CeleryInstrumentor tự inject/extract — không cần truyền tay).
configure_logging()
configure_tracing()
instrument_celery()
