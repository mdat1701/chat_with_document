"""Bảng `document` và `chunk` (SADD §3.1.1).

Giá trị hợp lệ của `document.status` — xem CL-05 (implement_plan.md
§9) và T-005 §6: SADD chưa thống nhất 100%, nhóm triển khai chốt tập
`processing | ready | failed | deleting` (đã báo lại Tech Lead).
`uploading` chỉ tồn tại phía client (SDD §3.7.1), không lưu DB.
"""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CHAR,
    BigInteger,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

DOCUMENT_STATUSES = ("processing", "ready", "failed", "deleting")


class Document(Base):
    __tablename__ = "document"
    __table_args__ = (
        # AC-007.2 / US-003: tên không phân biệt hoa-thường trong phạm vi
        # một owner_id (ER-08 trùng tên dựa trên chỉ mục này).
        Index(
            "ix_document_owner_name_unique",
            "owner_id",
            text("lower(name)"),
            unique=True,
            postgresql_where=text("status <> 'deleting'"),
        ),
        Index("ix_document_expires_at", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String, nullable=False, default="processing")
    error_code: Mapped[str | None] = mapped_column(String)
    blob_key: Mapped[str] = mapped_column(String, nullable=False)
    sha256: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    # `DateTime(timezone=True)` tường minh — bắt buộc: SQLAlchemy 2.0 ánh xạ
    # `Mapped[datetime]` trần (không chỉ định) thành TIMESTAMP WITHOUT TIME
    # ZONE ở phía Python/bind-param, lệch với cột DB thật
    # (`TIMESTAMP WITH TIME ZONE`, đúng theo migration) — INSERT một
    # `datetime.now(UTC)` (giá trị có tz, đúng chuẩn toàn bộ codebase) qua
    # ORM sẽ lỗi "can't subtract offset-naive and offset-aware datetimes"
    # ngay ở lần upload tài liệu đầu tiên. Lỗi chỉ lộ ra khi insert thật
    # qua Postgres thật bằng ORM (unit test trước đó toàn mock DB session).
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Chunk(Base):
    __tablename__ = "chunk"
    __table_args__ = (
        Index("ix_chunk_owner_document", "owner_id", "document_id"),
        Index("ix_chunk_tsv_gin", "tsv", postgresql_using="gin"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document.id", ondelete="CASCADE"), nullable=False
    )
    # Denormalized từ document.owner_id — lọc RLS không cần JOIN (SADD §3.1.1).
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    page_start: Mapped[int] = mapped_column(Integer, nullable=False)
    page_end: Mapped[int] = mapped_column(Integer, nullable=False)
    heading_path: Mapped[str | None] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Cột generated — KHÔNG ghi giá trị từ code ứng dụng (T-005 §5 bước 4).
    # Khớp đúng migration thật (immutable_unaccent — xem 0001_baseline.py):
    # unaccent() trần không IMMUTABLE, Postgres từ chối trong cột generated.
    tsv: Mapped[str] = mapped_column(
        TSVECTOR, Computed("to_tsvector('simple', immutable_unaccent(content))", persisted=True)
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024))
