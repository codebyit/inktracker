"""Add automation config for scheduled service-action logging.

Revision ID: 0008_automation_config
Revises: 0007_moisturizing_liquid
Create Date: 2026-05-19
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0008_automation_config"
down_revision = "0007_moisturizing_liquid"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return insp.has_table(table_name)


def upgrade() -> None:
    if not _table_exists("automation_config"):
        op.create_table(
            "automation_config",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("auto_maintenance_log_enabled", sa.Boolean, server_default=sa.text("true"), nullable=False),
            sa.Column("auto_maintenance_log_time", sa.String(5), server_default="03:00", nullable=False),
        )

    bind = op.get_bind()
    exists = bind.execute(sa.text("SELECT id FROM automation_config WHERE id = 1")).fetchone()
    if not exists:
        bind.execute(
            sa.text(
                "INSERT INTO automation_config (id, auto_maintenance_log_enabled, auto_maintenance_log_time) "
                "VALUES (1, :enabled, :run_time)"
            ),
            {"enabled": True, "run_time": "03:00"},
        )


def downgrade() -> None:
    if _table_exists("automation_config"):
        op.drop_table("automation_config")
