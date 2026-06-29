"""Add unique index on cartridge_inventory_lots.serial_number.

Revision ID: 0012_serial_number_unique
Revises: 0011_lot_serial_box_expiry
Create Date: 2026-05-31

SQLite treats every NULL as distinct, so a UNIQUE index on a nullable column
already allows multiple NULL rows without any partial-index workaround.
The same behaviour applies to PostgreSQL.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0012_serial_number_unique"
down_revision = "0011_lot_serial_box_expiry"
branch_labels = None
depends_on = None


def _index_exists(index_name: str) -> bool:
    """Return True if a named index already exists in the current database."""
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        rows = bind.execute(
            sa.text("SELECT name FROM sqlite_master WHERE type='index' AND name=:n"),
            {"n": index_name},
        ).fetchall()
    else:
        rows = bind.execute(
            sa.text(
                "SELECT indexname FROM pg_indexes WHERE indexname=:n"
            ),
            {"n": index_name},
        ).fetchall()
    return len(rows) > 0


def upgrade() -> None:
    if not _index_exists("uq_cartridge_inventory_lots_serial"):
        op.create_index(
            "uq_cartridge_inventory_lots_serial",
            "cartridge_inventory_lots",
            ["serial_number"],
            unique=True,
        )


def downgrade() -> None:
    op.drop_index(
        "uq_cartridge_inventory_lots_serial",
        table_name="cartridge_inventory_lots",
    )
