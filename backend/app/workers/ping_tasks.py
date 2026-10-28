"""Task mẫu để kiểm chứng định tuyến hàng đợi (T-006 §5 bước 3).

`ingestion.ping` phải tới hàng đợi `ingestion`, `maintenance.ping` tới
`maintenance` — theo `task_routes` trong `celery_app.py`.
"""

from app.workers.celery_app import celery_app


@celery_app.task(name="ingestion.ping")  # type: ignore[untyped-decorator]
def ingestion_ping() -> str:
    return "pong from ingestion queue"


@celery_app.task(name="maintenance.ping")  # type: ignore[untyped-decorator]
def maintenance_ping() -> str:
    return "pong from maintenance queue"
