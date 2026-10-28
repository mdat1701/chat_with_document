"""Bảng hạ tầng xuyên suốt, không thuộc riêng module nghiệp vụ nào
(SADD §3.1.1): `analytics_event` (US-020, allow-list — T-404) và
`audit_log` (ghi nhận hành động, không chứa tên tệp/nội dung).
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AnalyticsEvent(Base):
    __tablename__ = "analytics_event"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    user_hash: Mapped[str | None] = mapped_column(String)
    session_id: Mapped[str | None] = mapped_column(String)
    app_version: Mapped[str | None] = mapped_column(String)
    # Chỉ các trường đã qua allow-list (T-404) mới được ghi vào đây.
    props: Mapped[dict[str, object] | None] = mapped_column(JSONB)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str] = mapped_column(String, nullable=False)
    target_type: Mapped[str | None] = mapped_column(String)
    target_id: Mapped[str | None] = mapped_column(String)
    outcome: Mapped[str | None] = mapped_column(String)
