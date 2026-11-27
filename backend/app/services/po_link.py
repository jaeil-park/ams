"""
app/services/po_link.py — 파트 출고 ↔ 프로젝트 PO 번호 연결

파트 출고는 프로젝트를 직접 가리키지 않고 PO 번호(글자)로 연결된다.
그래서 PO 가 아직 없을 때 수기로 번호를 적어 먼저 불출하고, 나중에 같은 PO 의 프로젝트가 등록되면
따로 매칭하지 않아도 자동으로 이어진다.

- 비교는 항상 '정규화한 키'로 한다: 공백 제거 + 대문자 (po403813 / PO 403813 / PO403813 → 같은 PO)
- 프로젝트의 PO 번호가 바뀌면(PO 미발행 임시번호 → 실제 PO, 담당자 수정) relink_po 로
  옛 번호에 걸린 출고 기록·승인 대기 요청을 새 번호로 옮긴다.
"""

import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models

_SPACES = re.compile(r"\s+")


def normalize_po(value: str | None) -> str | None:
    """비교·저장용 PO 키. 비어 있으면 None."""
    if not value:
        return None
    key = _SPACES.sub("", value).upper()
    return key or None


def po_key_expr(column):
    """DB 컬럼을 normalize_po 와 같은 규칙으로 바꾼 SQL 식 (공백·탭·줄바꿈 제거 + 대문자)."""
    expr = column
    for ch in (" ", "\t", "\r", "\n"):
        expr = func.replace(expr, ch, "")
    return func.upper(expr)


def usage_po_filter(po_number: str | None):
    """이 PO 번호에 연결된 파트 출고를 고르는 조건. PO 가 비어 있으면 None."""
    key = normalize_po(po_number)
    if not key:
        return None
    return po_key_expr(models.PartUsage.po_number) == key


async def pending_usage_approvals(db: AsyncSession, po_number: str | None) -> list[models.Approval]:
    """이 PO 번호로 요청된 승인 대기 중 파트 출고. (payload 는 JSON 이라 파이썬에서 거른다)"""
    key = normalize_po(po_number)
    if not key:
        return []
    result = await db.execute(
        select(models.Approval).where(
            models.Approval.status == "PENDING",
            models.Approval.resource_type == "PART_USAGE",
        )
    )
    return [a for a in result.scalars().all() if normalize_po((a.payload or {}).get("po_number")) == key]


async def relink_po(db: AsyncSession, old_po: str | None, new_po: str | None) -> dict[str, int]:
    """
    옛 PO 번호에 걸린 파트 출고 기록과 승인 대기 요청을 새 번호로 옮긴다. 커밋은 호출한 쪽에서 한다.
    표기만 다른 같은 번호(po403813 → PO403813)면 저장값을 새 표기로 맞춘다.
    """
    old_key, new_value = normalize_po(old_po), normalize_po(new_po)
    if not old_key or not new_value:
        return {"usages": 0, "pending": 0}

    usages = (await db.execute(
        select(models.PartUsage).where(po_key_expr(models.PartUsage.po_number) == old_key)
    )).scalars().all()
    for u in usages:
        u.po_number = new_value
        db.add(u)

    pending = await pending_usage_approvals(db, old_po)
    for a in pending:
        # JSON 컬럼은 내부 값을 바꾸면 변경으로 잡히지 않으므로 새 dict 로 바꿔 넣는다
        a.payload = {**(a.payload or {}), "po_number": new_value}
        db.add(a)

    return {"usages": len(usages), "pending": len(pending)}
