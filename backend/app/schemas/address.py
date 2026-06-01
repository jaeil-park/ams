"""
app/schemas/address.py — Address Pydantic v2 스키마
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class AddressBase(BaseModel):
    customer_id: int
    location: str = Field(..., min_length=1, max_length=100)
    address: str = Field(..., min_length=1, max_length=500)
    memo: str | None = Field(None, max_length=500)


class AddressCreate(AddressBase):
    pass


class AddressUpdate(BaseModel):
    location: str | None = Field(None, min_length=1, max_length=100)
    address: str | None = Field(None, min_length=1, max_length=500)
    memo: str | None = Field(None, max_length=500)


class AddressOut(AddressBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
