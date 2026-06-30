"""Add inventory tracking tables and quantity counters.

Revision ID: 0009_inventory_tracking
Revises: 0008_automation_config
Create Date: 2026-05-23
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0009_inventory_tracking"
down_revision = "0008_automation_config"
branch_labels = None
depends_on = None


def _table_columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        rows = bind.execute(sa.text(f"PRAGMA table_info({table_name})")).fetchall()
        return {row[1] for row in rows}

    rows = bind.execute(
        sa.text("SELECT column_name FROM information_schema.columns WHERE table_name = :table_name"),
        {"table_name": table_name},
    ).fetchall()
    return {row[0] for row in rows}


def _add_column_if_missing(table_name: str, column_name: str, ddl: str) -> None:
    if column_name not in _table_columns(table_name):
        op.execute(sa.text(ddl))


def _create_table(stmt) -> None:
    """Execute a CREATE TABLE statement, making SERIAL primary keys SQLite-safe.

    ``id SERIAL PRIMARY KEY`` is PostgreSQL syntax. On SQLite, ``SERIAL`` does
    NOT create an autoincrementing rowid alias (only the exact type
    ``INTEGER PRIMARY KEY`` does), so any insert that omits ``id`` would store
    NULL and break ORM identity mapping. Rewrite it to ``INTEGER PRIMARY KEY``
    on SQLite; PostgreSQL keeps ``SERIAL`` unchanged.
    """
    ddl = getattr(stmt, "text", None) or str(stmt)
    if op.get_bind().dialect.name == "sqlite":
        ddl = ddl.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY")
    op.execute(sa.text(ddl))


def upgrade() -> None:
    _add_column_if_missing(
        "material_items",
        "quantity_added_total",
        "ALTER TABLE material_items ADD COLUMN quantity_added_total FLOAT DEFAULT 0",
    )
    _add_column_if_missing(
        "material_items",
        "quantity_consumed_total",
        "ALTER TABLE material_items ADD COLUMN quantity_consumed_total FLOAT DEFAULT 0",
    )

    _create_table(sa.text(
        """
        CREATE TABLE IF NOT EXISTS material_inventory_movements (
            id SERIAL PRIMARY KEY,
            material_item_id INTEGER NOT NULL REFERENCES material_items(id) ON DELETE CASCADE,
            project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
            movement_type VARCHAR(8) NOT NULL,
            quantity FLOAT NOT NULL DEFAULT 0,
            occurred_at TIMESTAMP,
            notes TEXT
        )
        """
    ))

    _create_table(sa.text(
        """
        CREATE TABLE IF NOT EXISTS cartridge_inventory_lots (
            id SERIAL PRIMARY KEY,
            channel VARCHAR(4) NOT NULL,
            quantity_ml FLOAT NOT NULL DEFAULT 0,
            expires_on VARCHAR(10),
            is_in_use BOOLEAN NOT NULL DEFAULT FALSE,
            installed_at TIMESTAMP,
            created_at TIMESTAMP,
            notes TEXT
        )
        """
    ))


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS cartridge_inventory_lots"))
    op.execute(sa.text("DROP TABLE IF EXISTS material_inventory_movements"))
