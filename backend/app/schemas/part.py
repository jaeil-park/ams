"""
app/schemas/part.py — PartInventory & Usage & Approval Pydantic v2 스키마
"""

from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


# ─── Part Inventory ────────────────────────────────
class PartInventoryBase(BaseModel):
    category: str = "PART"
    model: str = Field(..., min_length=1, max_length=100)
    qty: int = Field(0, ge=0)
    status: str = "IN_STOCK"
    location: str | None = Field(None, max_length=200)
    purchase_date: date | None = None
    warranty_end: date | None = None
    project_id: int | None = None


class PartInventoryCreate(PartInventoryBase):
    pass


class PartInventoryUpdate(BaseModel):
    model: str | None = Field(None, min_length=1, max_length=100)
    qty: int | None = Field(None, ge=0)
    status: str | None = None
    location: str | None = Field(None, max_length=200)
    purchase_date: date | None = None
    warranty_end: date | None = None
    project_id: int | None = None


class PartInventoryOut(PartInventoryBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ─── Part Usage ──────────────────────────────────
class PartUsageBase(BaseModel):
    part_id: int
    used_date: date
    customer_id: int
    location: str | None = Field(None, max_length=200)
    reason: str | None = Field(None, max_length=500)
    qty: int = Field(1, gt=0)


class PartUsageCreate(PartUsageBase):
    pass


class PartUsageOut(PartUsageBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ─── Approval (Admin 승인요청 관련) ───────────────
class ApprovalBase(BaseModel):
    resource_type: str = "PART_QTY"
    resource_id: int
    reason: str | None = Field(None, max_length=500)
    payload: dict  # 예: {"qty": 15}


class ApprovalCreate(ApprovalBase):
    pass


class ApprovalOut(ApprovalBase):
    id: int
    requester_id: int
    approver_id: int | None
    status: Literal["PENDING", "APPROVED", "REJECTED"]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
