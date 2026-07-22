"""Persist the wizard pre-prime overlay toggle per project.

Adds ``include_preprime`` (default true) to ``projects`` so the New/Edit
Project wizard can round-trip the "Include Pre-Prime Ink" toggle. This is a
display-only flag ΓÇö stored COGS is unchanged, since ``ink_cost`` is always
computed from the raw per-channel ``project_ink_usage`` rows.

Existing rows are backfilled to ``true`` to match the prior wizard default.

Additive, SQLite- and PostgreSQL-safe, idempotent, rollback-safe.

Revision ID: 0024_project_include_preprime
Revises: 0023_expiry_alert_days
Create Date: 2026-07-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0024_project_include_preprime"
down_revision = "0023_expiry_alert_days"
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
    if not _table_exists("projects"):
        return
    if "include_preprime" not in _table_columns("projects"):
        op.execute(sa.text(
            "ALTER TABLE projects ADD COLUMN include_preprime "
            "BOOLEAN NOT NULL DEFAULT TRUE"
        ))


def downgrade() -> None:
    # Non-destructive no-op: dropping a column on SQLite is awkward and a
    # rollback does not require removing this additive flag.
    pass
