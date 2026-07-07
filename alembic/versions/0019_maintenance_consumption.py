"""Correct maintenance consumption values to eufyMake per-channel spec.

Forward-effective corrections to system maintenance presets (see
``docs/maintenance-rules.md``). eufyMake support confirmed cleaning
(CLN) and moisturizing (ML) liquids are consumed **per ink channel** across the
machine's **6 active channels** (C, M, Y, K, W|FW, GL). Per-channel figures are
therefore multiplied by 6. The white position is a single slot (W XOR FW), so
maintenance presets target 6 channels rather than 7.

This migration UPDATES the volumes_json of existing **system** presets to the
corrected values and ADDS two new system presets (White Ink Flash Cleaning and
White Line Swap). It only rewrites preset definitions going forward; historical
``service_actions`` rows are left untouched (non-retroactive).

Idempotent, SQLite- and PostgreSQL-safe, rollback-safe.

Revision ID: 0019_maintenance_consumption
Revises: 0018_setup_completed
Create Date: 2026-07-05
"""

from __future__ import annotations

import json
from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision = "0019_maintenance_consumption"
down_revision = "0018_setup_completed"
branch_labels = None
depends_on = None


_CH = 6  # active channels: C, M, Y, K, (W|FW), GL
_ACTIVE = ["C", "M", "Y", "K", "W", "GL"]


def _r(value: float) -> float:
    return round(value, 2)


# name -> corrected volumes_json (system presets only)
_UPDATES: dict[str, str] = {
    "Ink Injection": json.dumps({c: 1.5 for c in _ACTIVE}),
    "Flash Clean": json.dumps({c: 0.0002 for c in _ACTIVE}),
    "Automatic Flash Clean": json.dumps({c: 0.0002 for c in _ACTIVE}),
    "Medium Clean": json.dumps({c: 0.2 for c in _ACTIVE}),
    "Deep Clean": json.dumps({**{c: 1.5 for c in _ACTIVE}, "CLN": _r(1.83 * _CH)}),
    "Automatic Deep Clean": json.dumps({"CLN": _r(1.5 * _CH)}),
    "Automatic Moisturizing": json.dumps({"CLN": _r(1.83 * _CH), "ML": _r(1.33 * _CH)}),
    "Safe Shutdown Moisturizing": json.dumps({"CLN": _r(1.83 * _CH), "ML": _r(1.33 * _CH)}),
    "Initial Startup": json.dumps({**{c: 15 for c in _ACTIVE}, "CLN": _r(4.67 * _CH)}),
    "Print Head Replacement": json.dumps({**{c: 15 for c in _ACTIVE}, "CLN": _r(4.67 * _CH)}),
    "Extended Shutdown Restart": json.dumps({**{c: 1.5 for c in _ACTIVE}, "CLN": _r(1.83 * _CH)}),
}

# name -> (kind, icon, color, tracks_ink, sort_order, volumes_json) for new presets
_NEW: dict[str, tuple] = {
    "Ink Injection (after Moisturizing)": (
        "quick_action", "syringe", "indigo", True, 15,
        json.dumps({**{c: 1.5 for c in _ACTIVE}, "CLN": _r(1.83 * _CH)}),
    ),
    "White Ink Flash Cleaning": (
        "quick_action", "bolt", "slate", True, 55,
        json.dumps({"W": 3.0, "CLN": _r(1.83 * _CH)}),
    ),
    "White Line Swap (Hard <-> Soft)": (
        "hardware_event", "droplet", "slate", True, 145,
        json.dumps({"W": 30.0}),
    ),
}


def _table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def upgrade() -> None:
    if not _table_exists("maintenance_presets"):
        return

    bind = op.get_bind()
    now = datetime.utcnow()

    # Forward-update existing system presets to corrected values.
    for name, vols in _UPDATES.items():
        bind.execute(
            sa.text(
                "UPDATE maintenance_presets SET volumes_json = :vols "
                "WHERE name = :name AND is_system = :is_sys"
            ),
            {"vols": vols, "name": name, "is_sys": True},
        )

    # Add new system presets if missing (idempotent by name).
    for name, (kind, icon, color, tracks_ink, sort_order, vols) in _NEW.items():
        row = bind.execute(
            sa.text("SELECT id FROM maintenance_presets WHERE name = :name"),
            {"name": name},
        ).fetchone()
        if row:
            continue
        bind.execute(
            sa.text(
                "INSERT INTO maintenance_presets "
                "(name, kind, icon, color, is_system, is_active, tracks_ink, "
                " sort_order, volumes_json, created_at) "
                "VALUES (:name, :kind, :icon, :color, :is_sys, :is_act, :tracks, "
                "        :sort, :vols, :created_at)"
            ),
            {
                "name": name,
                "kind": kind,
                "icon": icon,
                "color": color,
                "is_sys": True,
                "is_act": True,
                "tracks": tracks_ink,
                "sort": sort_order,
                "vols": vols,
                "created_at": now,
            },
        )


def downgrade() -> None:
    # Non-destructive: remove only the newly added presets. Prior corrected
    # values are left in place (restoring the old under-counted values would be
    # a regression, and historical service_actions are unaffected either way).
    if not _table_exists("maintenance_presets"):
        return
    bind = op.get_bind()
    for name in _NEW:
        bind.execute(
            sa.text(
                "DELETE FROM maintenance_presets "
                "WHERE name = :name AND is_system = :is_sys"
            ),
            {"name": name, "is_sys": True},
        )
