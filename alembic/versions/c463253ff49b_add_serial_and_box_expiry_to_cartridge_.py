"""add serial and box expiry to cartridge lots

Revision ID: c463253ff49b
Revises: 0011_lot_serial_box_expiry
Create Date: 2026-05-26 16:46:57.961683

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c463253ff49b'
down_revision: Union[str, None] = '0011_lot_serial_box_expiry'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {col["name"] for col in inspector.get_columns("cartridge_inventory_lots")}

    if "serial_number" not in existing_cols:
        op.add_column(
            "cartridge_inventory_lots",
            sa.Column("serial_number", sa.String(length=64), nullable=True),
        )
    if "box_expires_on" not in existing_cols:
        op.add_column(
            "cartridge_inventory_lots",
            sa.Column("box_expires_on", sa.String(length=10), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {col["name"] for col in inspector.get_columns("cartridge_inventory_lots")}

    if "box_expires_on" in existing_cols:
        op.drop_column("cartridge_inventory_lots", "box_expires_on")
    if "serial_number" in existing_cols:
        op.drop_column("cartridge_inventory_lots", "serial_number")
