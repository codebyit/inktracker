"""Add serial number and box expiry fields to cartridge lots.

Revision ID: 0011_lot_serial_box_expiry
Revises: 0010_inventory_alert_threshold
Create Date: 2026-05-26
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0011_lot_serial_box_expiry"
down_revision = "0010_inventory_alert_threshold"
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
    cols = _table_columns("cartridge_inventory_lots")

    if "serial_number" not in cols:
        op.execute(sa.text("ALTER TABLE cartridge_inventory_lots ADD COLUMN serial_number VARCHAR(64)"))

    if "box_expires_on" not in cols:
        op.execute(sa.text("ALTER TABLE cartridge_inventory_lots ADD COLUMN box_expires_on VARCHAR(10)"))


def downgrade() -> None:
    # No-op downgrade for cross-database safety.
    pass
