"""add disk3-5, extra_parts to server_inventories and po_number to part_usages

Revision ID: e5f6a7b8c9d0
Revises: d8b2f4a6c1e9
Create Date: 2026-07-27 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd8b2f4a6c1e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for n in (3, 4, 5):
        op.add_column('server_inventories', sa.Column(f'disk{n}_spec', sa.String(length=100), nullable=True))
        op.add_column('server_inventories', sa.Column(f'disk{n}_qty', sa.Integer(), nullable=True))
        op.add_column('server_inventories', sa.Column(f'disk{n}_raid', sa.String(length=50), nullable=True))
    op.add_column('server_inventories', sa.Column('extra_parts', sa.JSON(), nullable=True))
    op.add_column('part_usages', sa.Column('po_number', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('part_usages', 'po_number')
    op.drop_column('server_inventories', 'extra_parts')
    for n in (5, 4, 3):
        op.drop_column('server_inventories', f'disk{n}_raid')
        op.drop_column('server_inventories', f'disk{n}_qty')
        op.drop_column('server_inventories', f'disk{n}_spec')
