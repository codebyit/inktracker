"""Add configurable ink density (per channel) and cartridge tare (global).

These power the weight-based "remaining ink" helper so the conversion
weight(g) -> remaining(ml) accounts for real ink density instead of the
implicit 1 g/ml assumption. Defaults preserve the previous behavior:
density 1.0 g/ml and tare 75 g.

Revision ID: 0016_ink_density_and_tare
Revises: 0015_multi_craft
Create Date: 2026-06-29
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0016_ink_density_and_tare"
down_revision = "0015_multi_craft"
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
    if "ink_density_g_per_ml" not in _table_columns("ink_channel_config"):
        op.execute(sa.text(
            "ALTER TABLE ink_channel_config ADD COLUMN ink_density_g_per_ml FLOAT DEFAULT 1.0"
        ))
    if "cartridge_tare_g" not in _table_columns("ink_global_config"):
        op.execute(sa.text(
            "ALTER TABLE ink_global_config ADD COLUMN cartridge_tare_g FLOAT DEFAULT 75.0"
        ))


def downgrade() -> None:
    # Intentionally a no-op for safe downgrade behavior across SQLite/PostgreSQL.
    pass
