"""Add project_type column to projects.

Revision ID: 0013_project_type
Revises: 0012_serial_number_unique
Create Date: 2026-06-01

Adds a project_type field (commercial/gift/sample/internal) that drives
whether margin KPIs are meaningful for a project.  Existing rows default
to 'commercial' so nothing changes for current data.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0013_project_type"
down_revision = "0012_serial_number_unique"
branch_labels = None
depends_on = None


def _table_columns(table_name: str) -> list[str]:
    """Return column names for *table_name* in a dialect-safe way."""
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        rows = bind.execute(sa.text(f"PRAGMA table_info({table_name})")).fetchall()
        return [row[1] for row in rows]
    else:
        rows = bind.execute(
            sa.text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = :t"
            ),
            {"t": table_name},
        ).fetchall()
        return [row[0] for row in rows]


def upgrade() -> None:
    if "project_type" not in _table_columns("projects"):
        op.execute(
            sa.text(
                "ALTER TABLE projects ADD COLUMN project_type VARCHAR(20) NOT NULL DEFAULT 'commercial'"
            )
        )


def downgrade() -> None:
    # SQLite does not support DROP COLUMN prior to 3.35; skip silently on SQLite.
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.drop_column("projects", "project_type")
