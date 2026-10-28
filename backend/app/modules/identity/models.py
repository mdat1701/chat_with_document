"""Bảng `app_user` và `user_role` (SADD §3.1.1).

Tên cột khớp CHÍNH XÁC sơ đồ ER của SADD — không đổi tên tùy tiện
(T-005 §2, sai tên cột kéo theo sửa dây chuyền Sprint 1-4).
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import CITEXT, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

# Vai trò hợp lệ (SADD §3.1.1): user | manager | evaluator | admin.
VALID_ROLES = ("user", "manager", "evaluator", "admin")


class AppUser(Base):
    __tablename__ = "app_user"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    oidc_subject: Mapped[str | None] = mapped_column(String, unique=True)
    email: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserRole(Base):
    __tablename__ = "user_role"

    # Khóa chính ghép (user_id, role) — một người dùng có thể có nhiều vai trò.
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String, primary_key=True)
