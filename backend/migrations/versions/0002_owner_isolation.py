"""Enable and enforce owner isolation for user-owned tables (T-104)."""

from collections.abc import Sequence

from alembic import op

revision: str = "0002_owner_isolation"
down_revision: str | Sequence[str] | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table in ("document", "chunk", "answer", "feedback"):
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY owner_isolation ON {table}
            USING (owner_id = current_setting('app.user_id')::uuid)
            WITH CHECK (owner_id = current_setting('app.user_id')::uuid)
            """
        )


def downgrade() -> None:
    for table in ("feedback", "answer", "chunk", "document"):
        op.execute(f"DROP POLICY IF EXISTS owner_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
