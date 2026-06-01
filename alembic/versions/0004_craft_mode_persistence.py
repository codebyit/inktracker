"""Add craft ink mode and craft mode params persistence fields.

Revision ID: 0004_craft_mode
Revises: 0003_lifecycle
Create Date: 2026-05-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004_craft_mode"
down_revision = "0003_lifecycle"
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
    _add_column_if_missing("projects", "craft_ink_mode", "ALTER TABLE projects ADD COLUMN craft_ink_mode VARCHAR(50) DEFAULT ''")
    _add_column_if_missing("projects", "craft_mode_params_json", "ALTER TABLE projects ADD COLUMN craft_mode_params_json TEXT DEFAULT '{}'")
    _add_column_if_missing("print_templates", "craft_ink_mode", "ALTER TABLE print_templates ADD COLUMN craft_ink_mode VARCHAR(50) DEFAULT ''")
    _add_column_if_missing("print_templates", "craft_mode_params_json", "ALTER TABLE print_templates ADD COLUMN craft_mode_params_json TEXT DEFAULT '{}'")


def downgrade() -> None:
    pass
