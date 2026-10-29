"""baseline

Revision ID: 0001_baseline
Revises:
Create Date: 2026-10-28

Tạo 8 bảng cốt lõi (SADD §3.1.1), chỉ mục (§3.1.2), 2 vai trò CSDL và
bật Row-Level Security trên document/chunk/answer/feedback (T-005).
Policy RLS thật (USING owner_id = current_setting('app.user_id')) là
T-104 — task này chỉ ENABLE, chưa viết policy.

Viết tay (không qua `--autogenerate`) vì môi trường triển khai không
có PostgreSQL chạy sẵn để Alembic so sánh — xem T-005 "Ghi chú triển
khai thực tế".
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql as pg

revision: str = "0001_baseline"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Extension (T-002 đã tạo ở infra/pg-init cho local; migration
    # tự tạo lại idempotent để staging/CI cũng có, theo đúng thứ tự
    # extension -> bảng -> chỉ mục -> vai trò -> RLS (T-005 §4). ---
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    # `unaccent()` của contrib tự khai báo STABLE, không phải IMMUTABLE —
    # Postgres từ chối dùng nó trong biểu thức GENERATED ALWAYS ... STORED
    # bên dưới ("generation expression is not immutable"), lỗi chỉ lộ ra
    # khi chạy thật trên Postgres (chưa từng phát hiện vì môi trường triển
    # khai các task T-005/T-202 không có Postgres thật để chạy migration).
    # Khắc phục chuẩn (PostgreSQL wiki): bọc lại bằng một hàm SQL khai báo
    # IMMUTABLE tường minh, gọi unaccent() qua object dictionary cố định.
    op.execute(
        "CREATE OR REPLACE FUNCTION immutable_unaccent(text) RETURNS text AS $$ "
        "SELECT unaccent('unaccent', $1) "
        "$$ LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT"
    )

    # --- app_user ---
    op.create_table(
        "app_user",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("oidc_subject", sa.String(), unique=True),
        sa.Column("email", pg.CITEXT(), nullable=False, unique=True),
        sa.Column("display_name", sa.String()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("granted_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )

    # --- user_role ---
    op.create_table(
        "user_role",
        sa.Column(
            "user_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("app_user.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("role", sa.String(), primary_key=True),
    )

    # --- document ---
    op.create_table(
        "document",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("app_user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("page_count", sa.Integer()),
        sa.Column("status", sa.String(), nullable=False, server_default="processing"),
        sa.Column("error_code", sa.String()),
        sa.Column("blob_key", sa.String(), nullable=False),
        sa.Column("sha256", sa.CHAR(64), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ready_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
    )
    # Danh sách tài liệu mới nhất trước, bỏ qua bản ghi đã xóa (SADD §3.1.2).
    # Dùng `op.execute` thay vì `op.create_index(..., sa.text(...))`: xác
    # nhận bằng cách chạy thật trên Postgres rằng cơ chế nội bộ của Alembic
    # cho cột biểu thức (`_textual_index_element`, dùng chung một đối
    # tượng `Table` ảo cho các lệnh `create_index` liên tiếp trên cùng một
    # bảng) làm WHERE của chỉ mục TRƯỚC đó bị lặp lại nhầm sang chỉ mục
    # SAU — lỗi chỉ lộ ra khi chạy thật, không phải lỗi cú pháp để lint bắt
    # được. SQL thô loại bỏ hẳn nguồn gây lỗi này.
    op.execute(
        "CREATE INDEX ix_document_owner_uploaded_at ON document "
        "(owner_id, uploaded_at DESC) WHERE status <> 'deleting'"
    )
    # ER-08: trùng tên không phân biệt hoa-thường trong phạm vi một owner
    # (giữ đúng phạm vi gốc — không WHERE, áp dụng cho mọi trạng thái).
    op.execute(
        "CREATE UNIQUE INDEX ix_document_owner_name_unique ON document "
        "(owner_id, lower(name))"
    )
    op.create_index("ix_document_expires_at", "document", ["expires_at"])

    # --- chunk ---
    op.create_table(
        "chunk",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "document_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("document.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("owner_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=False),
        sa.Column("page_end", sa.Integer(), nullable=False),
        sa.Column("heading_path", sa.String()),
        sa.Column("content", sa.Text(), nullable=False),
        # Cột generated — KHÔNG ghi giá trị từ code ứng dụng (T-005 §5 bước 4).
        sa.Column(
            "tsv",
            pg.TSVECTOR(),
            sa.Computed(
                "to_tsvector('simple', immutable_unaccent(content))", persisted=True
            ),
        ),
        sa.Column("embedding", Vector(1024)),
    )
    op.create_index("ix_chunk_owner_document", "chunk", ["owner_id", "document_id"])
    op.create_index("ix_chunk_tsv_gin", "chunk", ["tsv"], postgresql_using="gin")
    # HNSW cho chunk.embedding: CHƯA tạo — ADR-05 chỉ bật khi > 2 triệu chunk.

    # --- answer (KHÔNG có cột nội dung — P-03/ADR-10) ---
    op.create_table(
        "answer",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("app_user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("conversation_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("turn_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("answer_type", sa.String()),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("citation_count", sa.Integer()),
        sa.Column("cited_doc_count", sa.Integer()),
        sa.Column("prompt_version", sa.String()),
        sa.Column("model_id", sa.String()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_answer_owner_created", "answer", ["owner_id", "created_at"])

    # --- feedback (post-MVP, tạo sẵn tối thiểu — T-005 §5 bước 6) ---
    op.create_table(
        "feedback",
        sa.Column(
            "answer_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("answer.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("owner_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("rating", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- analytics_event (US-020) ---
    op.create_table(
        "analytics_event",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_hash", sa.String()),
        sa.Column("session_id", sa.String()),
        sa.Column("app_version", sa.String()),
        sa.Column("props", pg.JSONB()),
    )
    op.create_index("ix_analytics_event_name_ts", "analytics_event", ["name", "ts"])

    # --- audit_log ---
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_id", pg.UUID(as_uuid=True)),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("target_type", sa.String()),
        sa.Column("target_id", sa.String()),
        sa.Column("outcome", sa.String()),
    )

    # --- Row-Level Security (chỉ ENABLE; policy là T-104) ---
    for table in ("document", "chunk", "answer", "feedback"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    # --- Vai trò CSDL (T-005 §3) ---
    # Mật khẩu thật được cấp sau, ngoài migration (secret manager — T-004/D-02).
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'cwd_app') THEN "
        "CREATE ROLE cwd_app LOGIN; "
        "END IF; END $$;"
    )
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'cwd_worker') THEN "
        "CREATE ROLE cwd_worker LOGIN BYPASSRLS; "
        "END IF; END $$;"
    )
    for table in (
        "app_user",
        "user_role",
        "document",
        "chunk",
        "answer",
        "feedback",
        "analytics_event",
        "audit_log",
    ):
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO cwd_app, cwd_worker")
    # `chunk.id`/`analytics_event.id`/`audit_log.id` là BIGSERIAL — Postgres
    # tự tạo một sequence riêng cho mỗi cột, SỞ HỮU bởi `postgres` (vai trò
    # chạy migration), KHÔNG tự kèm theo GRANT ở trên (GRANT trên bảng
    # không bao gồm quyền trên sequence của nó). Thiếu dòng này, INSERT
    # bằng vai trò `cwd_app` thật sẽ lỗi "permission denied for sequence"
    # ngay ở `nextval()` — lỗi chỉ lộ ra khi chạy thật bằng đúng vai trò
    # ứng dụng (không phải `postgres`), chưa từng phát hiện vì môi trường
    # triển khai T-005 không có Postgres thật để kiểm.
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO cwd_app, cwd_worker")


def downgrade() -> None:
    op.execute("REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM cwd_app, cwd_worker")
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM cwd_app, cwd_worker")
    op.execute("DROP ROLE IF EXISTS cwd_app")
    op.execute("DROP ROLE IF EXISTS cwd_worker")

    op.drop_table("audit_log")
    op.drop_table("analytics_event")
    op.drop_table("feedback")
    op.drop_index("ix_answer_owner_created", table_name="answer")
    op.drop_table("answer")
    op.drop_index("ix_chunk_tsv_gin", table_name="chunk")
    op.drop_index("ix_chunk_owner_document", table_name="chunk")
    op.drop_table("chunk")
    op.drop_index("ix_document_expires_at", table_name="document")
    op.drop_index("ix_document_owner_name_unique", table_name="document")
    op.drop_index("ix_document_owner_uploaded_at", table_name="document")
    op.drop_table("document")
    op.drop_table("user_role")
    op.execute("DROP FUNCTION IF EXISTS immutable_unaccent(text)")
    op.drop_table("app_user")
