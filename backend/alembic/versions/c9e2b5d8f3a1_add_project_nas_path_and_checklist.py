"""add nas_path and completion checklist to projects

NAS 납품문서 폴더 연동과 완료 처리 체크리스트를 위한 컬럼을 추가한다.

Revision ID: c9e2b5d8f3a1
Revises: d4f8a2c6e1b7
Create Date: 2026-09-28 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9e2b5d8f3a1'
down_revision: Union[str, None] = 'd4f8a2c6e1b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('nas_path', sa.String(length=1000), nullable=True))
    op.add_column('projects', sa.Column('completion_checklist', sa.JSON(), nullable=True))
    op.add_column('projects', sa.Column('completed_at', sa.DateTime(), nullable=True))
    op.add_column('projects', sa.Column('completed_by', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_projects_completed_by_users', 'projects', 'users', ['completed_by'], ['id']
    )


def downgrade() -> None:
    op.drop_constraint('fk_projects_completed_by_users', 'projects', type_='foreignkey')
    op.drop_column('projects', 'completed_by')
    op.drop_column('projects', 'completed_at')
    op.drop_column('projects', 'completion_checklist')
    op.drop_column('projects', 'nas_path')
