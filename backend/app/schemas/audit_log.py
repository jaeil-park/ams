"""
app/schemas/audit_log.py — AuditLog Pydantic 스키마
"""

from datetime import datetime
from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: int
    user_id: int | None
    action: str
    resource_type: str
    resource_id: int | None
    before: dict | None
    after: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}
