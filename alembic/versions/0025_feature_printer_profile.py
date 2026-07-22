"""Persist the selected printer profile for per-profile wizard options.

Adds ``printer_profile`` (default ``eufymake_e1``) to ``feature_config`` so the
New/Edit Project wizard can scope options ΓÇö notably the print-quality list ΓÇö
to the user's printer. eufyMake Studio has no "Ultra" quality; other/custom
printers keep it.

Existing rows are backfilled to ``eufymake_e1`` (the primary profile / prior
implicit default).

Additive, SQLite- and PostgreSQL-safe, idempotent, rollback-safe.

Revision ID: 0025_feature_printer_profile
Revises: 0024_project_include_preprime
Create Date: 2026-07-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0025_feature_printer_profile"
down_revision = "0024_project_include_preprime"
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
    if not _table_exists("feature_config"):
        return
    if "printer_profile" not in _table_columns("feature_config"):
        op.execute(sa.text(
            "ALTER TABLE feature_config ADD COLUMN printer_profile "
            "VARCHAR(40) NOT NULL DEFAULT 'eufymake_e1'"
        ))


def downgrade() -> None:
    # Non-destructive no-op: dropping a column on SQLite is awkward and a
    # rollback does not require removing this additive setting.
    pass
