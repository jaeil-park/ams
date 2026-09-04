"""
app/schemas/system_log.py — SystemLog Pydantic 스키마
"""

from datetime import datetime
from pydantic import BaseModel


class SystemLogOut(BaseModel):
    id: int
    level: str
    method: str
    path: str
    status_code: int
    user_email: str | None
    message: str | None
    detail: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
