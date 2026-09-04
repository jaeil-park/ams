"""add part_number and notes to part_inventories

Revision ID: b3d7e9f2a1c8
Revises: f1a2b3c4d5e6
Create Date: 2026-09-04 06:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3d7e9f2a1c8'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('part_inventories', sa.Column('part_number', sa.String(length=100), nullable=True))
    op.add_column('part_inventories', sa.Column('notes', sa.String(length=2000), nullable=True))


def downgrade() -> None:
    op.drop_column('part_inventories', 'notes')
    op.drop_column('part_inventories', 'part_number')
