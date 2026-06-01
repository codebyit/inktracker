"""Merge multiple heads into single linear history.

This migration exists solely to resolve the multiple-head state that arose
from repeated failed stamp attempts leaving extra rows in alembic_version.

Revision ID: 0002_merge_heads
Revises: 0001
Create Date: 2026-05-12
"""

from __future__ import annotations

from alembic import op


revision = "0002_merge_heads"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
