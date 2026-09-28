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
    part_number: str | None = Field(None, max_length=100)
    qty: int = Field(0, ge=0)
    status: str = "IN_STOCK"
    location: str | None = Field(None, max_length=200)
    notes: str | None = Field(None, max_length=2000)
    purchase_date: date | None = None
    warranty_end: date | None = None
    project_id: int | None = None


class PartInventoryCreate(PartInventoryBase):
    pass


class PartInventoryUpdate(BaseModel):
    category: str | None = None
    model: str | None = Field(None, min_length=1, max_length=100)
    part_number: str | None = Field(None, max_length=100)
    qty: int | None = Field(None, ge=0)
    status: str | None = None
    location: str | None = Field(None, max_length=200)
    notes: str | None = Field(None, max_length=2000)
    purchase_date: date | None = None
    warranty_end: date | None = None
    project_id: int | None = None


class PartInventoryOut(PartInventoryBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ─── Part Usage ──────────────────────────────────
class PartUsageCreate(BaseModel):
    # part_id는 URL 경로(/parts/{id}/usage)로 전달되므로 요청 본문에는 불필요
    used_date: date | None = None
    customer_id: int
    location: str | None = Field(None, max_length=200)
    reason: str | None = Field(None, max_length=500)
    qty: int = Field(1, gt=0)
    po_number: str | None = Field(None, max_length=100)


class PartUsageOut(BaseModel):
    id: int
    part_id: int
    used_date: date
    customer_id: int
    location: str | None = None
    reason: str | None = None
    qty: int
    po_number: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PartUsageHistoryOut(BaseModel):
    """전체 파트 출고 이력 — 어떤 파트가 어디로 나갔는지 한 줄로 읽히도록 이름을 함께 싣는다."""
    id: int
    part_id: int
    part_model: str | None = None
    part_number: str | None = None
    category: str | None = None
    used_date: date
    qty: int
    customer_id: int | None = None
    customer_name: str | None = None
    po_number: str | None = None
    location: str | None = None
    reason: str | None = None
    created_at: datetime


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

    # 대상 자원의 사람이 읽을 수 있는 이름 (예: 'Dell 300GB SAS HDD (400-AJOQ)').
    # DB에 저장되지 않는 파생 값으로, 목록 조회 시 채워 넣는다.
    resource_label: str | None = None

    model_config = ConfigDict(from_attributes=True)
