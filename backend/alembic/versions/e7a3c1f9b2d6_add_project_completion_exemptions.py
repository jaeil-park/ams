"""add completion_exemptions to projects

완료 체크리스트 자동 검사의 예외 처리 내역(사유·처리자·시각)을 보관한다.

Revision ID: e7a3c1f9b2d6
Revises: b2c3d4e5f6a8
Create Date: 2026-11-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7a3c1f9b2d6'
down_revision: Union[str, None] = 'b2c3d4e5f6a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('completion_exemptions', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('projects', 'completion_exemptions')
