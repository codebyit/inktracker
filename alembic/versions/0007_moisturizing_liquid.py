"""Add Moisturizing Liquid (ML) channel and seed two moisturizing presets.

Revision ID: 0007_moisturizing_liquid
Revises: 0006_service_maintenance
Create Date: 2026-05-19
"""

from __future__ import annotations

import json
from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision = "0007_moisturizing_liquid"
down_revision = "0006_service_maintenance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    now = datetime.utcnow()

    # ── InkChannelConfig row for ML ───────────────────────────────────────────
    row = bind.execute(
        sa.text("SELECT id FROM ink_channel_config WHERE channel = 'ML'")
    ).fetchone()
    if not row:
        bind.execute(
            sa.text(
                "INSERT INTO ink_channel_config "
                "(channel, price_per_cartridge, cartridge_capacity_ml, preprime_ml) "
                "VALUES ('ML', 0.0, 500.0, 0.0)"
            )
        )

    # ── Moisturizing presets ──────────────────────────────────────────────────
    presets = [
        ("Automatic Moisturizing",    50, json.dumps({"ML": 1.33})),
        ("Safe Shutdown Moisturizing", 60, json.dumps({"ML": 1.33})),
    ]
    for name, sort_order, volumes_json in presets:
        row = bind.execute(
            sa.text("SELECT id FROM maintenance_presets WHERE name = :name"),
            {"name": name},
        ).fetchone()
        if not row:
            bind.execute(
                sa.text(
                    "INSERT INTO maintenance_presets "
                    "(name, kind, icon, color, is_system, is_active, tracks_ink, "
                    " sort_order, volumes_json, created_at) "
                    "VALUES (:name, 'quick_action', 'droplet', 'emerald', "
                    "        :is_sys, :is_act, :tracks, :sort, :vols, :created_at)"
                ),
                {
                    "name": name,
                    "is_sys": True,
                    "is_act": True,
                    "tracks": True,
                    "sort": sort_order,
                    "vols": volumes_json,
                    "created_at": now,
                },
            )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM maintenance_presets "
            "WHERE name IN ('Automatic Moisturizing', 'Safe Shutdown Moisturizing') "
            "AND is_system = :is_sys"
        ),
        {"is_sys": True},
    )
    bind.execute(
        sa.text("DELETE FROM ink_channel_config WHERE channel = 'ML'")
    )
