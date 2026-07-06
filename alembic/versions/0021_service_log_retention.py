"""Add Service Action Log retention settings to automation_config.

Adds ``service_log_archive_days`` (default 60) and ``service_log_purge_days``
(default 365) to ``automation_config``. Archived entries are hidden from the
default Service Action Log view but retained; purged entries are permanently
deleted by the maintenance scheduler.

Additive, SQLite- and PostgreSQL-safe, idempotent, rollback-safe.

Revision ID: 0021_service_log_retention
Revises: 0020_ml_capacity_125
Create Date: 2026-07-06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0021_service_log_retention"
down_revision = "0020_ml_capacity_125"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _table_columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        rows = bind.execute(sa.text(f"PRAGMA table_info({table_name})")).fetchall()
        return {row[1] for row in rows}
    rows = bind.execute(
        sa.text("SELECT column_name FROM information_schema.columns WHERE table_name = :t"),
        {"t": table_name},
    ).fetchall()
    return {row[0] for row in rows}


def upgrade() -> None:
    if not _table_exists("automation_config"):
        return
    cols = _table_columns("automation_config")
    if "service_log_archive_days" not in cols:
        op.execute(sa.text(
            "ALTER TABLE automation_config ADD COLUMN service_log_archive_days "
            "INTEGER NOT NULL DEFAULT 60"
        ))
    if "service_log_purge_days" not in cols:
        op.execute(sa.text(
            "ALTER TABLE automation_config ADD COLUMN service_log_purge_days "
            "INTEGER NOT NULL DEFAULT 365"
        ))


def downgrade() -> None:
    # Non-destructive no-op: dropping columns on SQLite is awkward and a rollback
    # does not require removing these additive settings.
    pass
