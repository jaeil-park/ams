"""add warranty lookup queue, worker status, warranty service_level/detail

Revision ID: a1b2c3d4e5f7
Revises: c9e2b5d8f3a1
Create Date: 2026-10-02 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, None] = 'c9e2b5d8f3a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('warranties', sa.Column('service_level', sa.String(length=200), nullable=True))
    op.add_column('warranties', sa.Column('detail', sa.JSON(), nullable=True))

    op.create_table(
        'warranty_lookups',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('batch_id', sa.String(length=36), nullable=False),
        sa.Column('serial_tag', sa.String(length=100), nullable=False),
        sa.Column('vendor', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('inventory_id', sa.Integer(), nullable=True),
        sa.Column('apply_to_inventory', sa.Boolean(), nullable=False),
        sa.Column('applied', sa.Boolean(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('service_level', sa.String(length=200), nullable=True),
        sa.Column('product_name', sa.String(length=200), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('detail', sa.JSON(), nullable=True),
        sa.Column('error', sa.String(length=500), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('requested_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['inventory_id'], ['server_inventories.id']),
        sa.ForeignKeyConstraint(['requested_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_warranty_lookups_batch_id'), 'warranty_lookups', ['batch_id'], unique=False)
    op.create_index(op.f('ix_warranty_lookups_serial_tag'), 'warranty_lookups', ['serial_tag'], unique=False)
    op.create_index(op.f('ix_warranty_lookups_status'), 'warranty_lookups', ['status'], unique=False)

    op.create_table(
        'warranty_worker_statuses',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('state', sa.String(length=30), nullable=False),
        sa.Column('message', sa.String(length=500), nullable=True),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )


def downgrade() -> None:
    op.drop_table('warranty_worker_statuses')
    op.drop_index(op.f('ix_warranty_lookups_status'), table_name='warranty_lookups')
    op.drop_index(op.f('ix_warranty_lookups_serial_tag'), table_name='warranty_lookups')
    op.drop_index(op.f('ix_warranty_lookups_batch_id'), table_name='warranty_lookups')
    op.drop_table('warranty_lookups')
    op.drop_column('warranties', 'detail')
    op.drop_column('warranties', 'service_level')
