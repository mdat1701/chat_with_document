"""Bảng `answer` (SADD §3.1.1).

CHỦ Ý không có cột nội dung câu hỏi/câu trả lời — chỉ metadata, theo
ADR-10 và nguyên tắc P-03 (US-020: số liệu không chứa nội dung).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Answer(Base):
    __tablename__ = "answer"
    __table_args__ = (Index("ix_answer_owner_created", "owner_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    answer_type: Mapped[str | None] = mapped_column(String)  # answered|partial|not_found
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    citation_count: Mapped[int | None] = mapped_column(Integer)
    cited_doc_count: Mapped[int | None] = mapped_column(Integer)
    prompt_version: Mapped[str | None] = mapped_column(String)
    model_id: Mapped[str | None] = mapped_column(String)
    # `DateTime(timezone=True)` tường minh — xem ghi chú ở
    # `app/modules/documents/models.py::Document.uploaded_at`.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
