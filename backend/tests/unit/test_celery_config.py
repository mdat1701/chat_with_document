"""Kiểm thử cấu hình Celery (T-006 §7) — không cần Redis chạy thật:
chỉ kiểm tra cấu hình và định tuyến, là phần có thể xác minh mà không
cần hạ tầng (SADD §2.2.4, §4.2.2, §4.2.3).
"""

import app.workers.blob_tasks  # noqa: F401
import app.workers.ingestion_tasks  # noqa: F401
import app.workers.ping_tasks  # noqa: F401
import app.workers.retention_tasks  # noqa: F401
from app.workers.celery_app import celery_app


def test_acks_late_enabled() -> None:
    """Job được trả lại hàng đợi nếu worker chết giữa chừng (SADD §4.2.2)."""
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True


def test_prefetch_multiplier_is_one() -> None:
    """Task nặng (ingestion) không nên bị gom trước."""
    assert celery_app.conf.worker_prefetch_multiplier == 1


def test_time_limits_match_reap_stuck_threshold() -> None:
    """soft_time_limit phải khớp ngưỡng reap_stuck 10 phút (T-207)."""
    assert celery_app.conf.task_soft_time_limit == 10 * 60
    assert celery_app.conf.task_time_limit == 15 * 60


def test_all_six_tasks_are_registered() -> None:
    names = {n for n in celery_app.tasks if not n.startswith("celery.")}
    assert names == {
        "ingestion.ping",
        "maintenance.ping",
        "ingestion.process",
        "retention.purge_expired",
        "blob.reconcile_orphans",
        "maintenance.reap_stuck",
    }


def test_ingestion_tasks_route_to_ingestion_queue() -> None:
    for name in ("ingestion.ping", "ingestion.process"):
        options = celery_app.amqp.router.route({}, name)
        assert options["queue"].name == "ingestion"


def test_maintenance_tasks_route_to_maintenance_queue() -> None:
    for name in (
        "maintenance.ping",
        "retention.purge_expired",
        "blob.reconcile_orphans",
        "maintenance.reap_stuck",
    ):
        options = celery_app.amqp.router.route({}, name)
        assert options["queue"].name == "maintenance"


def test_broker_uses_separate_redis_db_from_sessions() -> None:
    """SADD §2.3: DB Redis riêng cho broker, tách khỏi phiên/rate limit."""
    from app.core.config import get_settings

    settings = get_settings()
    assert settings.celery_broker_url != settings.redis_url
    assert celery_app.conf.broker_url == settings.celery_broker_url
