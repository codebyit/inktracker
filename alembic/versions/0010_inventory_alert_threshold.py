"""Add configurable inventory low-stock threshold.

Revision ID: 0010_inventory_alert_threshold
Revises: 0009_inventory_tracking
Create Date: 2026-05-23
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0010_inventory_alert_threshold"
down_revision = "0009_inventory_tracking"
branch_labels = None
depends_on = None


def _table_columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        rows = bind.execute(sa.text(f"PRAGMA table_info({table_name})")).fetchall()
        return {row[1] for row in rows}

    rows = bind.execute(
        sa.text("SELECT column_name FROM information_schema.columns WHERE table_name = :table_name"),
        {"table_name": table_name},
    ).fetchall()
    return {row[0] for row in rows}


def upgrade() -> None:
    if "low_inventory_lot_pct" not in _table_columns("ink_global_config"):
        op.execute(sa.text("ALTER TABLE ink_global_config ADD COLUMN low_inventory_lot_pct FLOAT DEFAULT 25"))


def downgrade() -> None:
    # Intentionally left no-op for safe downgrade behavior across SQLite/PostgreSQL.
    pass
