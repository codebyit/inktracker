"""Add project lifecycle columns: status, completed_at, deleted_at, archived.

Revision ID: 0003_lifecycle
Revises: 0002_merge_heads
Create Date: 2026-05-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_lifecycle"
down_revision = "0002_merge_heads"
branch_labels = None
depends_on = None


def _table_columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        rows = bind.execute(sa.text(f"PRAGMA table_info({table_name})")).fetchall()
        return {row[1] for row in rows}
    rows = bind.execute(sa.text(
        "SELECT column_name FROM information_schema.columns WHERE table_name = :table_name"
    ), {"table_name": table_name}).fetchall()
    return {row[0] for row in rows}


def _add_column_if_missing(table_name: str, column_name: str, ddl: str) -> None:
    if column_name not in _table_columns(table_name):
        op.execute(sa.text(ddl))


def upgrade() -> None:
    _add_column_if_missing("projects", "status", "ALTER TABLE projects ADD COLUMN status VARCHAR(20) DEFAULT 'Completed'")
    _add_column_if_missing("projects", "completed_at", "ALTER TABLE projects ADD COLUMN completed_at TIMESTAMP")
    _add_column_if_missing("projects", "deleted_at", "ALTER TABLE projects ADD COLUMN deleted_at TIMESTAMP")
    _add_column_if_missing("projects", "archived", "ALTER TABLE projects ADD COLUMN archived BOOLEAN DEFAULT FALSE")
    # Backfill existing rows: treat all existing projects as already completed
    op.execute(sa.text(
        "UPDATE projects SET completed_at = created_at WHERE completed_at IS NULL"
    ))
    op.execute(sa.text(
        "UPDATE projects SET archived = FALSE WHERE archived IS NULL"
    ))


def downgrade() -> None:
    pass
