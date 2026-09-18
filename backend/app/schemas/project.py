"""
app/schemas/project.py — Project Pydantic v2 스키마
"""

from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


class ProjectBase(BaseModel):
    po_number: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    customer_id: int
    manager: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=255)
    status: Literal["WAITING", "IN_PROGRESS", "COMPLETED"] = "WAITING"
    location: str | None = Field(None, max_length=500)
    scheduled_date: date | None = None

    # PO 문서 기준값 — 실제값과 별도로 보관한다 (납품이 PO대로 되지 않는 경우가 정상적으로 있음)
    po_amount: int | None = None
    po_currency: str | None = Field(None, max_length=10)
    po_delivery_date: date | None = None
    po_variance_note: str | None = Field(None, max_length=500)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    po_number: str | None = Field(None, min_length=1, max_length=100)
    name: str | None = Field(None, min_length=1, max_length=200)
    customer_id: int | None = None
    manager: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=255)
    status: Literal["WAITING", "IN_PROGRESS", "COMPLETED"] | None = None
    location: str | None = Field(None, max_length=500)
    scheduled_date: date | None = None

    po_amount: int | None = None
    po_currency: str | None = Field(None, max_length=10)
    po_delivery_date: date | None = None
    po_variance_note: str | None = Field(None, max_length=500)


class ProjectOut(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime

    # PO 문서 첨부 여부 (필수 문서 누락을 목록에서 바로 알아보기 위한 파생 값)
    has_po: bool = False

    model_config = ConfigDict(from_attributes=True)
