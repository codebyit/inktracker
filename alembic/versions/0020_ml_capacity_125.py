"""Correct Moisturizing Liquid (ML) cartridge capacity 500 -> 125 ml.

The moisturizer is one compartment of the single physical "UV Cleaning
Cartridge" (cleaning solution 255 ml, moisturizer 125 ml, waste ink 125 ml per
the eufyMake wiki). InkTrack previously seeded ML at 500 ml, which overstates
moisturizer capacity ~4x and delays low-ML refill warnings.

Forward-effective: only rows still at the old 500.0 default are corrected, so a
user's deliberately customized ML capacity is left untouched. SQLite- and
PostgreSQL-safe, idempotent, rollback-safe.

Revision ID: 0020_ml_capacity_125
Revises: 0019_maintenance_consumption
Create Date: 2026-07-05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0020_ml_capacity_125"
down_revision = "0019_maintenance_consumption"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def upgrade() -> None:
    if not _table_exists("ink_channel_config"):
        return
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE ink_channel_config SET cartridge_capacity_ml = 125.0 "
            "WHERE channel = 'ML' AND cartridge_capacity_ml = 500.0"
        )
    )


def downgrade() -> None:
    if not _table_exists("ink_channel_config"):
        return
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE ink_channel_config SET cartridge_capacity_ml = 500.0 "
            "WHERE channel = 'ML' AND cartridge_capacity_ml = 125.0"
        )
    )
