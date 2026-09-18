"""add project_attachments

Revision ID: a7c1e3b9d2f4
Revises: b3d7e9f2a1c8
Create Date: 2026-09-18 05:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7c1e3b9d2f4'
down_revision: Union[str, None] = 'b3d7e9f2a1c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'project_attachments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('content_type', sa.String(length=150), nullable=True),
        sa.Column('size', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('kind', sa.String(length=30), nullable=False, server_default='OTHER'),
        sa.Column('note', sa.String(length=500), nullable=True),
        sa.Column('data', sa.LargeBinary(), nullable=False),
        sa.Column('uploaded_by', sa.Integer(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_project_attachments_project_id'), 'project_attachments', ['project_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_project_attachments_project_id'), table_name='project_attachments')
    op.drop_table('project_attachments')
