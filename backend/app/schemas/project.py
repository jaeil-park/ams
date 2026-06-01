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
    status: Literal["WAITING", "IN_PROGRESS", "COMPLETED"] = "WAITING"
    location: str | None = Field(None, max_length=500)
    scheduled_date: date | None = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    po_number: str | None = Field(None, min_length=1, max_length=100)
    name: str | None = Field(None, min_length=1, max_length=200)
    customer_id: int | None = None
    manager: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=50)
    status: Literal["WAITING", "IN_PROGRESS", "COMPLETED"] | None = None
    location: str | None = Field(None, max_length=500)
    scheduled_date: date | None = None


class ProjectOut(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
