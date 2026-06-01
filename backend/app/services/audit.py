"""
app/services/audit.py — 감사 로그(AuditLog) 공통 유틸
- 모든 CUD 엔드포인트에서 호출하여 변경 이력을 자동 기록합니다.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog


async def log_action(
    db: AsyncSession,
    *,
    user_id: int | None,
    action: str,          # "CREATE" | "UPDATE" | "DELETE"
    resource_type: str,   # "CUSTOMER" | "SERVER" | "PART" | "PROJECT" | ...
    resource_id: int | None = None,
    before: dict | None = None,
    after: dict | None = None,
) -> AuditLog:
    """
    CUD 작업 후 AuditLog 레코드를 생성합니다.
    세션은 호출자(엔드포인트)에서 commit 합니다.
    """
    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        before=before,
        after=after,
    )
    db.add(entry)
    return entry
