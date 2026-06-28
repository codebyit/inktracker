"""Merge the two open migration heads into a single linear tip.

Before this migration the revision graph had two heads, both descending from
``0011_lot_serial_box_expiry``:

    0011 ──> 0012_serial_number_unique ──> 0013_project_type   (head)
    0011 ──> c463253ff49b                                       (head)

``c463253ff49b`` adds ``serial_number`` / ``box_expires_on`` to
``cartridge_inventory_lots`` — the same columns ``0011`` already adds with
existence guards — so applying it is idempotent. Production applies both heads
via ``alembic upgrade heads`` (see docker-entrypoint.sh), so unifying them here
changes nothing about what gets applied; it only restores a single head so that
``alembic upgrade head`` (singular, used by app/migration_runner.py) works again.

This is an empty merge migration: it carries no schema operations of its own.

Revision ID: 0014_merge_heads
Revises: 0013_project_type, c463253ff49b
Create Date: 2026-06-28
"""
from __future__ import annotations


revision = "0014_merge_heads"
down_revision = ("0013_project_type", "c463253ff49b")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
