"""Bảng `feedback` (SADD §3.1.1) — post-MVP (US-018), tạo sẵn ở dạng
tối thiểu và BẬT RLS ngay từ T-005 để không quên khi tính năng được
duyệt sau MVP-lite (T-005 §5 bước 6). Không có use case/API nào dùng
bảng này trong MVP-lite.

Ghi chú triển khai: SADD chỉ liệt kê `answer_id, rating, updated_at`.
Đã thêm `owner_id` denormalized (cùng mẫu với `chunk.owner_id`) để
policy RLS (T-104) lọc trực tiếp mà không cần subquery sang `answer`.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Feedback(Base):
    __tablename__ = "feedback"

    answer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("answer.id", ondelete="CASCADE"), primary_key=True
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    rating: Mapped[str] = mapped_column(String, nullable=False)  # up | down
    # `DateTime(timezone=True)` tường minh — xem ghi chú ở
    # `app/modules/documents/models.py::Document.uploaded_at`.
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
