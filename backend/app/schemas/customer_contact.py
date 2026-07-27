"""
app/schemas/customer_contact.py — CustomerContact Pydantic v2 스키마
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class CustomerContactBase(BaseModel):
    customer_id: int
    name: str = Field(..., min_length=1, max_length=100)
    phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=255)


class CustomerContactCreate(CustomerContactBase):
    pass


class CustomerContactUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=255)


class CustomerContactOut(CustomerContactBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
