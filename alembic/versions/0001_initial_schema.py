"""Initial schema — idempotent bootstrap for fresh and existing databases.

Uses raw SQL (CREATE TABLE IF NOT EXISTS, ADD COLUMN IF NOT EXISTS) to avoid
SQLAlchemy inspect() and the removed op.get_bind() API (removed Alembic 1.10).
Safe against both completely empty DBs and existing DBs missing newer columns.

Revision ID: 0001
Revises:
Create Date: 2026-05-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "0001"
down_revision = "20260503_01"  # chains after the original migration file
branch_labels = None
depends_on = None


def _table_columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        rows = bind.execute(sa.text(f"PRAGMA table_info({table_name})")).fetchall()
        return {row[1] for row in rows}
    rows = bind.execute(sa.text(
        "SELECT column_name FROM information_schema.columns WHERE table_name = :table_name"
    ), {"table_name": table_name}).fetchall()
    return {row[0] for row in rows}


def _add_column_if_missing(table_name: str, column_name: str, ddl: str) -> None:
    if column_name not in _table_columns(table_name):
        op.execute(sa.text(ddl))


def upgrade() -> None:
    # ── machine_config ────────────────────────────────────────────────────────
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS machine_config (
            id                 SERIAL PRIMARY KEY,
            purchase_price     FLOAT DEFAULT 2500,
            setup_cost         FLOAT DEFAULT 0,
            lifespan_hours     FLOAT DEFAULT 10000,
            annual_hours       FLOAT DEFAULT 500,
            power_watts        FLOAT DEFAULT 250,
            electricity_rate   FLOAT DEFAULT 0.13,
            annual_maintenance FLOAT DEFAULT 499
        )
    """))
    _add_column_if_missing("machine_config", "setup_cost", "ALTER TABLE machine_config ADD COLUMN setup_cost FLOAT DEFAULT 0")

    # ── ink_channel_config ────────────────────────────────────────────────────
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS ink_channel_config (
            id                    SERIAL PRIMARY KEY,
            channel               VARCHAR(4) NOT NULL UNIQUE,
            price_per_cartridge   FLOAT DEFAULT 45,
            cartridge_capacity_ml FLOAT DEFAULT 100,
            preprime_ml           FLOAT DEFAULT 0
        )
    """))
    _add_column_if_missing("ink_channel_config", "preprime_ml", "ALTER TABLE ink_channel_config ADD COLUMN preprime_ml FLOAT DEFAULT 0")

    # ── ink_global_config ─────────────────────────────────────────────────────
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS ink_global_config (
            id                    SERIAL PRIMARY KEY,
            cartridge_capacity_ml FLOAT DEFAULT 100,
            white_loaded          VARCHAR(4) DEFAULT 'W',
            low_ink_pct           FLOAT DEFAULT 20,
            currency              VARCHAR(8) DEFAULT '€'
        )
    """))

    # ── labor_config ──────────────────────────────────────────────────────────
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS labor_config (
            id           SERIAL PRIMARY KEY,
            hourly_rate  FLOAT DEFAULT 15,
            overhead_pct FLOAT DEFAULT 25
        )
    """))

    # ── margin_config ─────────────────────────────────────────────────────────
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS margin_config (
            id                 SERIAL PRIMARY KEY,
            retail_minimum     FLOAT DEFAULT 30,
            retail_target      FLOAT DEFAULT 50,
            retail_strong      FLOAT DEFAULT 65,
            wholesale_minimum  FLOAT DEFAULT 20,
            wholesale_target   FLOAT DEFAULT 35,
            wholesale_strong   FLOAT DEFAULT 50
        )
    """))
    for col, default in [
        ("retail_minimum", 30), ("retail_target", 50), ("retail_strong", 65),
        ("wholesale_minimum", 20), ("wholesale_target", 35), ("wholesale_strong", 50),
    ]:
        _add_column_if_missing(
            "margin_config",
            col,
            f"ALTER TABLE margin_config ADD COLUMN {col} FLOAT DEFAULT {default}",
        )

    # ── projects ──────────────────────────────────────────────────────────────
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS projects (
            id                  SERIAL PRIMARY KEY,
            name                VARCHAR(200) NOT NULL,
            created_at          TIMESTAMP,
            units               INTEGER DEFAULT 1,
            sell_price_per_unit FLOAT DEFAULT 0,
            print_time_hours    FLOAT DEFAULT 0,
            hands_on_hours      FLOAT DEFAULT 0,
            ink_mode            VARCHAR(50) DEFAULT 'CMYK',
            print_quality       VARCHAR(20) DEFAULT 'Standard',
            photo_path          VARCHAR(500),
            notes               TEXT,
            print_bed           VARCHAR(20) DEFAULT 'Standard',
            alignment           VARCHAR(20) DEFAULT 'Photo',
            craft_mode          VARCHAR(30) DEFAULT 'Flat',
            substrate           VARCHAR(50) DEFAULT '',
            white_choke_mm      FLOAT DEFAULT 0.2,
            layer_stack_json    TEXT DEFAULT '[]',
            ink_cost            FLOAT DEFAULT 0,
            bom_cost            FLOAT DEFAULT 0,
            machine_cost        FLOAT DEFAULT 0,
            labor_cost          FLOAT DEFAULT 0,
            overhead_cost       FLOAT DEFAULT 0,
            total_cogs          FLOAT DEFAULT 0,
            cogs_per_unit       FLOAT DEFAULT 0,
            total_revenue       FLOAT DEFAULT 0,
            total_profit        FLOAT DEFAULT 0,
            margin_pct          FLOAT DEFAULT 0,
            margin_status       VARCHAR(20) DEFAULT ''
        )
    """))
    # Add wizard step-1 columns that may be missing from older schema
    for col, col_type, default in [
        ("print_bed",        "VARCHAR(20)", "'Standard'"),
        ("alignment",        "VARCHAR(20)", "'Photo'"),
        ("craft_mode",       "VARCHAR(30)", "'Flat'"),
        ("craft_ink_mode",   "VARCHAR(50)", "''"),
        ("craft_mode_params_json", "TEXT", "'{}'"),
        ("substrate",        "VARCHAR(50)", "''"),
        ("white_choke_mm",   "FLOAT",       "0.2"),
        ("layer_stack_json", "TEXT",        "'[]'"),
    ]:
        _add_column_if_missing(
            "projects",
            col,
            f"ALTER TABLE projects ADD COLUMN {col} {col_type} DEFAULT {default}",
        )

    # ── project_ink_usage ─────────────────────────────────────────────────────
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS project_ink_usage (
            id         SERIAL PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id),
            channel    VARCHAR(4) NOT NULL,
            ml_used    FLOAT DEFAULT 0
        )
    """))

    # ── bom_items ─────────────────────────────────────────────────────────────
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS bom_items (
            id         SERIAL PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id),
            name       VARCHAR(200) NOT NULL,
            quantity   FLOAT DEFAULT 1,
            unit       VARCHAR(20) DEFAULT 'pcs',
            unit_cost  FLOAT DEFAULT 0,
            total_cost FLOAT DEFAULT 0
        )
    """))

    # ── print_templates ───────────────────────────────────────────────────────
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS print_templates (
            id               SERIAL PRIMARY KEY,
            name             VARCHAR(200) NOT NULL,
            created_at       TIMESTAMP,
            print_bed        VARCHAR(20) DEFAULT 'Standard',
            alignment        VARCHAR(20) DEFAULT 'Photo',
            material         VARCHAR(50) DEFAULT 'Ceramics',
            substrate        VARCHAR(50) DEFAULT '',
            print_quality    VARCHAR(20) DEFAULT 'Standard',
            white_choke_mm   FLOAT DEFAULT 0.2,
            craft_mode       VARCHAR(30) DEFAULT 'Flat',
            ink_mode         VARCHAR(50) DEFAULT 'CMYK',
            layer_stack_json TEXT DEFAULT '[]'
        )
    """))
    for col, col_type, default in [
        ("craft_ink_mode", "VARCHAR(50)", "''"),
        ("craft_mode_params_json", "TEXT", "'{}'"),
    ]:
        _add_column_if_missing(
            "print_templates",
            col,
            f"ALTER TABLE print_templates ADD COLUMN {col} {col_type} DEFAULT {default}",
        )

    # ── material_categories ───────────────────────────────────────────────────
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS material_categories (
            id         SERIAL PRIMARY KEY,
            name       VARCHAR(100) NOT NULL UNIQUE,
            sort_order INTEGER DEFAULT 0
        )
    """))

    # ── material_items ────────────────────────────────────────────────────────
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS material_items (
            id         SERIAL PRIMARY KEY,
            name       VARCHAR(200) NOT NULL,
            category   VARCHAR(100) NOT NULL DEFAULT 'Other',
            unit_cost  FLOAT DEFAULT 0,
            unit       VARCHAR(20) DEFAULT 'pcs',
            created_at TIMESTAMP
        )
    """))

    # ── cartridge_replacements ────────────────────────────────────────────────
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS cartridge_replacements (
            id          SERIAL PRIMARY KEY,
            channel     VARCHAR(4) NOT NULL,
            replaced_at TIMESTAMP,
            notes       TEXT
        )
    """))

    # ── maintenance_events ────────────────────────────────────────────────────
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS maintenance_events (
            id          SERIAL PRIMARY KEY,
            event_type  VARCHAR(50) NOT NULL,
            occurred_at TIMESTAMP,
            cost        FLOAT DEFAULT 0,
            notes       TEXT
        )
    """))


def downgrade() -> None:
    # Downgrade not implemented for initial idempotent bootstrap migration.
    pass
