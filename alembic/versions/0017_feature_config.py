"""Persist the multi-craft feature flag as an app setting (feature_config).

Moves ``MULTI_CRAFT_ENABLED`` from an environment variable to a single-row
``feature_config`` table so it is configurable from Settings > Preferences and
shared by both the Docker and Windows desktop builds. Seeds the initial value
from the ``MULTI_CRAFT_ENABLED`` env var when it is explicitly set (backward
compatibility for existing deployments); otherwise defaults to enabled, since
the feature is now generally available.

Additive and rollback-safe.

Revision ID: 0017_feature_config
Revises: 0016_ink_density_and_tare
Create Date: 2026-07-01
"""

from __future__ import annotations

import os

from alembic import op
import sqlalchemy as sa


revision = "0017_feature_config"
down_revision = "0016_ink_density_and_tare"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _seed_default() -> bool:
    raw = os.environ.get("MULTI_CRAFT_ENABLED", "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return True  # feature is GA: default on when the env var is unset


def upgrade() -> None:
    if not _table_exists("feature_config"):
        op.create_table(
            "feature_config",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column(
                "multi_craft_enabled",
                sa.Boolean,
                server_default=sa.text("true"),
                nullable=False,
            ),
        )

    bind = op.get_bind()
    exists = bind.execute(sa.text("SELECT id FROM feature_config WHERE id = 1")).fetchone()
    if not exists:
        bind.execute(
            sa.text("INSERT INTO feature_config (id, multi_craft_enabled) VALUES (1, :enabled)"),
            {"enabled": _seed_default()},
        )


def downgrade() -> None:
    if _table_exists("feature_config"):
        op.drop_table("feature_config")
