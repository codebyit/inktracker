"""Add material persistence to projects.

Revision ID: 0005_project_material
Revises: 0004_craft_mode
Create Date: 2026-05-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0005_project_material"
down_revision = "0004_craft_mode"
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


def upgrade() -> None:
    if "material" not in _table_columns("projects"):
        op.execute(sa.text("ALTER TABLE projects ADD COLUMN material VARCHAR(50) DEFAULT 'Ceramics'"))


def downgrade() -> None:
    pass
