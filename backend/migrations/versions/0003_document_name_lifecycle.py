"""Allow replacing a document while its old blob is being deleted (T-108)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_document_name_lifecycle"
down_revision: str | Sequence[str] | None = "0002_owner_isolation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_document_owner_name_unique", table_name="document")
    op.create_index(
        "ix_document_owner_name_unique",
        "document",
        ["owner_id", "lower(name)"],
        unique=True,
        postgresql_where=sa.text("status <> 'deleting'"),
    )


def downgrade() -> None:
    op.drop_index("ix_document_owner_name_unique", table_name="document")
    op.create_index(
        "ix_document_owner_name_unique",
        "document",
        ["owner_id", "lower(name)"],
        unique=True,
    )
