"""Ghi sự kiện sản phẩm tối thiểu qua allow-list (US-020, trong
phạm vi MVP-lite). Tổng hợp báo cáo tuần (US-019) là post-MVP -
không cài đặt trong module này cho đến khi được duyệt.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.models import AnalyticsEvent

logger = logging.getLogger(__name__)

ALLOWED_EVENTS = {
    "session_started", "empty_state_viewed", "document_upload_started",
    "document_upload_rejected_client", "document_processing_succeeded",
    "document_processing_failed", "document_deleted", "question_submitted",
    "answer_rendered", "answer_failed", "retry_clicked", "citation_viewed",
    "upload_started", "upload_completed", "feedback_submitted",
}


def _hash(value: str) -> str:
    return hmac.new(
        get_settings().analytics_hash_secret.encode(), value.encode(), hashlib.sha256
    ).hexdigest()


async def record_event(
    session: AsyncSession,
    name: str,
    *,
    user_id: UUID | None = None,
    sid: str | None = None,
    props: dict[str, object] | None = None,
) -> None:
    """`sid` là cookie `cwd_sid` THÔ (chưa băm) lấy từ phiên HTTP — hàm
    này tự băm một chiều trước khi ghi, giống `user_id` (T-404 §5 bước 3).
    Sự kiện phát từ worker (không có phiên HTTP) truyền `sid=None`."""
    if name not in ALLOWED_EVENTS:
        logger.warning("analytics event rejected: %s", name)
        return
    allowed_props = {
        "latency_ms", "answer_type", "citation_count", "file_size_bytes", "status",
        "is_first_session", "state_code", "file_size_bucket", "reason_code",
        "page_count", "duration_ms", "error_code", "trigger", "question_length",
        "language", "ready_doc_count", "context", "citation_index",
    }
    safe_props = {
        key: value for key, value in (props or {}).items()
        if key in allowed_props
    }
    rejected_props = set(props or {}) - allowed_props
    if rejected_props:
        logger.warning("analytics properties rejected: %s", sorted(rejected_props))
    session.add(
        AnalyticsEvent(
            name=name,
            ts=datetime.now(UTC),
            user_hash=_hash(str(user_id)) if user_id is not None else None,
            session_id=_hash(sid) if sid is not None else None,
            app_version=get_settings().app_version,
            props=safe_props,
        )
    )
