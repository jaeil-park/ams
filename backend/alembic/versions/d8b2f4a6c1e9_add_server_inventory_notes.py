"""add server_inventories notes column

Revision ID: d8b2f4a6c1e9
Revises: c3a9f1e2b7d4
Create Date: 2026-07-27 13:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8b2f4a6c1e9'
down_revision: Union[str, None] = 'c3a9f1e2b7d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('server_inventories', sa.Column('notes', sa.String(length=2000), nullable=True))


def downgrade() -> None:
    op.drop_column('server_inventories', 'notes')
