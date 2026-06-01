"""
app/schemas/customer.py — Customer Pydantic v2 스키마
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


class CustomerBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    biz_no: str | None = Field(None, max_length=50)
    manager: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=50)
    status: Literal["ACTIVE", "INACTIVE"] = "ACTIVE"


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    code: str | None = Field(None, min_length=1, max_length=50)
    name: str | None = Field(None, min_length=1, max_length=100)
    biz_no: str | None = Field(None, max_length=50)
    manager: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=50)
    status: Literal["ACTIVE", "INACTIVE"] | None = None


class CustomerOut(CustomerBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
