"""add PO reference fields to projects

PO 문서 기준값(금액/통화/요구납기)과 차이 사유를 실제값과 별도로 보관한다.
실제 납품이 PO대로 이루어지지 않는 경우가 정상적으로 존재하기 때문이다.

Revision ID: d4f8a2c6e1b7
Revises: a7c1e3b9d2f4
Create Date: 2026-09-18 06:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4f8a2c6e1b7'
down_revision: Union[str, None] = 'a7c1e3b9d2f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('po_amount', sa.Integer(), nullable=True))
    op.add_column('projects', sa.Column('po_currency', sa.String(length=10), nullable=True))
    op.add_column('projects', sa.Column('po_delivery_date', sa.Date(), nullable=True))
    op.add_column('projects', sa.Column('po_variance_note', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('projects', 'po_variance_note')
    op.drop_column('projects', 'po_delivery_date')
    op.drop_column('projects', 'po_currency')
    op.drop_column('projects', 'po_amount')
