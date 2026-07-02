"""Add first-run setup_completed flag to feature_config.

Adds a ``setup_completed`` boolean to ``feature_config`` powering the first-time
setup wizard. On a fresh database the column defaults to False so the wizard
prompt shows. **Existing installs are backfilled to True** so they are never
nagged with onboarding for a database that is already configured.

Additive, SQLite-safe, and rollback-safe (mirrors 0017_feature_config).

Revision ID: 0018_setup_completed
Revises: 0017_feature_config
Create Date: 2026-07-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0018_setup_completed"
down_revision = "0017_feature_config"
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
    bind = op.get_bind()

    # feature_config is created by 0017; guard in case of an unusual state.
    if not _table_exists("feature_config"):
        op.create_table(
            "feature_config",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("multi_craft_enabled", sa.Boolean,
                      server_default=sa.text("true"), nullable=False),
        )
        bind.execute(sa.text(
            "INSERT INTO feature_config (id, multi_craft_enabled) VALUES (1, true)"
        ))

    # Add the column with a False server default (correct for brand-new rows).
    if "setup_completed" not in _table_columns("feature_config"):
        op.execute(sa.text(
            "ALTER TABLE feature_config ADD COLUMN setup_completed BOOLEAN "
            "NOT NULL DEFAULT FALSE"
        ))
        # Backfill: mark setup complete ONLY for an EXISTING install so it is not
        # nagged with onboarding. We must not key off "does the feature_config row
        # exist" — migration 0017 inserts that row even on a brand-new database.
        # The reliable signal is whether the app has been seeded/used before:
        # ``seed_defaults`` runs at app startup (AFTER migrations), so on a fresh
        # database ``machine_config`` (and projects) are still empty during this
        # migration, whereas an existing install already has them.
        existing_install = False
        for tbl in ("machine_config", "projects"):
            if _table_exists(tbl):
                row = bind.execute(sa.text(f"SELECT 1 FROM {tbl} LIMIT 1")).fetchone()
                if row:
                    existing_install = True
                    break
        if existing_install:
            bind.execute(sa.text("UPDATE feature_config SET setup_completed = TRUE"))

    # Ensure the singleton row exists (fresh DB path where 0017 seeded it will
    # have id=1 already; leave setup_completed at its column default of False).
    exists = bind.execute(sa.text("SELECT id FROM feature_config WHERE id = 1")).fetchone()
    if not exists:
        bind.execute(sa.text(
            "INSERT INTO feature_config (id, multi_craft_enabled, setup_completed) "
            "VALUES (1, true, false)"
        ))


def downgrade() -> None:
    # Non-destructive no-op: dropping a single column is awkward on SQLite and
    # unnecessary for a safe rollback.
    pass
