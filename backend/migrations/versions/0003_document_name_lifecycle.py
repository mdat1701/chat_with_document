"""Allow replacing a document while its old blob is being deleted (T-108)."""

from collections.abc import Sequence

from alembic import op

revision: str = "0003_document_name_lifecycle"
down_revision: str | Sequence[str] | None = "0002_owner_isolation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # `op.create_index(..., ["owner_id", "lower(name)"])` với "lower(name)"
    # là CHUỖI THƯỜNG (không phải sa.text()/sa.literal_column()) bị Alembic
    # hiểu nhầm thành TÊN CỘT theo nghĩa đen (`_textual_index_column`), nên
    # DDL sinh ra trích dẫn `"lower(name)"` như một định danh — lỗi
    # "column \"lower(name)\" does not exist" khi chạy thật trên Postgres.
    # Lỗi này chưa từng lộ ra vì môi trường triển khai T-108 không có
    # Postgres thật để chạy migration (xem ghi chú T-005/T-108). Dùng SQL
    # thô để tránh toàn bộ cơ chế `_textual_index_column` dễ vỡ của Alembic.
    op.execute("DROP INDEX IF EXISTS ix_document_owner_name_unique")
    op.execute(
        "CREATE UNIQUE INDEX ix_document_owner_name_unique ON document "
        "(owner_id, lower(name)) WHERE status <> 'deleting'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_owner_name_unique")
    op.execute(
        "CREATE UNIQUE INDEX ix_document_owner_name_unique ON document (owner_id, lower(name))"
    )
