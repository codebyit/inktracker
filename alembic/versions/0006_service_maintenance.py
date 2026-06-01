"""Service & maintenance redesign: presets, service actions, cleaning channel.

Revision ID: 0006_service_maintenance
Revises: 0005_project_material
Create Date: 2026-05-16
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0006_service_maintenance"
down_revision = "0005_project_material"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return insp.has_table(table_name)


def upgrade() -> None:
    # Drop legacy maintenance_events (superseded by service_actions).
    if _table_exists("maintenance_events"):
        op.drop_table("maintenance_events")

    if not _table_exists("maintenance_presets"):
        op.create_table(
            "maintenance_presets",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("kind", sa.String(20), nullable=False),
            sa.Column("icon", sa.String(40), nullable=True),
            sa.Column("color", sa.String(20), nullable=True),
            sa.Column("is_system", sa.Boolean, server_default=sa.text("false"), nullable=False),
            sa.Column("is_active", sa.Boolean, server_default=sa.text("true"), nullable=False),
            sa.Column("tracks_ink", sa.Boolean, server_default=sa.text("true"), nullable=False),
            sa.Column("sort_order", sa.Integer, server_default="0", nullable=False),
            sa.Column("volumes_json", sa.Text, server_default="{}", nullable=False),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        )

    if not _table_exists("service_actions"):
        op.create_table(
            "service_actions",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("preset_id", sa.Integer, sa.ForeignKey("maintenance_presets.id", ondelete="SET NULL"), nullable=True),
            sa.Column("kind", sa.String(20), nullable=False),
            sa.Column("name_snapshot", sa.String(100), nullable=False),
            sa.Column("occurred_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
            sa.Column("volumes_json", sa.Text, server_default="{}", nullable=False),
            sa.Column("total_ml", sa.Float, server_default="0", nullable=False),
            sa.Column("notes", sa.Text, nullable=True),
        )


def downgrade() -> None:
    # One-way migration; legacy maintenance_events is not restored.
    pass
