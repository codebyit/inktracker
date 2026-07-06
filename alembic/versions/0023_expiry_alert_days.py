"""Add configurable cartridge-lot expiry alert window.

Adds ``expiry_alert_days`` (default 30) to ``ink_global_config``. This unifies
the previously hard-coded 30-day expiry window used by the Dashboard alerts and
the Inventory "expiring soon" highlighting, and lets non-eufyMake printer
profiles tune how early they want to be warned.

Additive, SQLite- and PostgreSQL-safe, idempotent, rollback-safe.

Revision ID: 0023_expiry_alert_days
Revises: 0022_white_swap_both_whites
Create Date: 2026-07-06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0023_expiry_alert_days"
down_revision = "0022_white_swap_both_whites"
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
    if not _table_exists("ink_global_config"):
        return
    if "expiry_alert_days" not in _table_columns("ink_global_config"):
        op.execute(sa.text(
            "ALTER TABLE ink_global_config ADD COLUMN expiry_alert_days "
            "INTEGER NOT NULL DEFAULT 30"
        ))


def downgrade() -> None:
    # Non-destructive no-op: dropping a column on SQLite is awkward and a
    # rollback does not require removing this additive setting.
    pass
