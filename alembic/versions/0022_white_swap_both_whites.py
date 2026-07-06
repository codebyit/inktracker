"""Show both whites on the White Line Swap preset (W + FW).

The White Line Swap event consumes ~30 ml of the newly installed white ink.
Since Hard White (W) and Soft/Flexible White (FW) share one slot, the preset now
carries both channels (W:30, FW:0) so the log form shows both and the user records
the ~30 ml on whichever white is being installed. Forward-updates the existing
system preset row; hardware-event inputs are already restricted to a preset's
channels in the UI.

Additive/data-only, SQLite- and PostgreSQL-safe, idempotent, rollback-safe.

Revision ID: 0022_white_swap_both_whites
Revises: 0021_service_log_retention
Create Date: 2026-07-06
"""

from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa


revision = "0022_white_swap_both_whites"
down_revision = "0021_service_log_retention"
branch_labels = None
depends_on = None

_NAME = "White Line Swap (Hard <-> Soft)"


def _table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def upgrade() -> None:
    if not _table_exists("maintenance_presets"):
        return
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE maintenance_presets SET volumes_json = :vols "
            "WHERE name = :name AND is_system = :is_sys"
        ),
        {"vols": json.dumps({"W": 30.0, "FW": 0.0}), "name": _NAME, "is_sys": True},
    )


def downgrade() -> None:
    if not _table_exists("maintenance_presets"):
        return
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE maintenance_presets SET volumes_json = :vols "
            "WHERE name = :name AND is_system = :is_sys"
        ),
        {"vols": json.dumps({"W": 30.0}), "name": _NAME, "is_sys": True},
    )
