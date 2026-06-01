"""Initial schema

Revision ID: 20260503_01
Revises:
Create Date: 2026-05-03

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260503_01"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Compatibility shim: the idempotent migration chain now lives in 0001+.
    # Keeping this revision as a no-op prevents table-exists failures when an
    # existing database is re-upgraded.
    pass


def downgrade() -> None:
    op.drop_table("bom_items")
    op.drop_table("project_ink_usage")
    op.drop_table("maintenance_events")
    op.drop_table("cartridge_replacements")
    op.drop_table("material_items")
    op.drop_table("material_categories")
    op.drop_table("print_templates")
    op.drop_table("projects")
    op.drop_table("margin_config")
    op.drop_table("labor_config")
    op.drop_table("ink_global_config")
    op.drop_table("ink_channel_config")
    op.drop_table("machine_config")
