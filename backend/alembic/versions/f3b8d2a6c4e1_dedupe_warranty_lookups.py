"""hide duplicated warranty_lookups (keep one row per serial + vendor)

같은 시리얼을 조회할 때마다 행이 새로 생기던 문제로 쌓인 중복 기록을 숨긴다 (행 삭제 아님).
시리얼·제조사마다 완료 건 → 서버 반영 건 → 최신 건 순으로 1건만 남긴다.

Revision ID: f3b8d2a6c4e1
Revises: e7a3c1f9b2d6
Create Date: 2026-11-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f3b8d2a6c4e1'
down_revision: Union[str, None] = 'e7a3c1f9b2d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE warranty_lookups SET is_deleted = true
        WHERE id IN (
            SELECT id FROM (
                SELECT id, ROW_NUMBER() OVER (
                    PARTITION BY serial_tag, vendor
                    ORDER BY CASE WHEN status = 'DONE' THEN 0 ELSE 1 END,
                             CASE WHEN applied THEN 0 ELSE 1 END,
                             id DESC
                ) AS rn
                FROM warranty_lookups WHERE is_deleted = false
            ) t WHERE rn > 1
        )
    """)


def downgrade() -> None:
    # 어떤 행이 중복으로 숨겨졌는지 구분할 수 없으므로 되돌리지 않는다
    pass
