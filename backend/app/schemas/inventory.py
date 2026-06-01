"""
app/schemas/inventory.py — ServerInventory Pydantic v2 스키마
"""

from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


class ServerInventoryBase(BaseModel):
    serial_tag: str = Field(..., min_length=1, max_length=100)
    category: Literal["SERVER"] = "SERVER"
    model: str = Field(..., min_length=1, max_length=100)
    vendor: str | None = Field(None, max_length=100)
    status: Literal["IN_STOCK", "RESERVED", "SCHEDULED", "DELIVERED", "RMA"] = "IN_STOCK"
    project_id: int | None = None
    in_date: date | None = None
    
    # OS & Network
    host_name: str | None = Field(None, max_length=100)
    service_ip: str | None = Field(None, max_length=50)
    mgmt_ip: str | None = Field(None, max_length=50)
    
    # Specs
    cpu_model: str | None = Field(None, max_length=100)
    cpu_core: int | None = None
    mem_capacity: int | None = None
    mem_gen: str | None = Field(None, max_length=50)
    mem_qty: int | None = None
    
    disk1_spec: str | None = Field(None, max_length=100)
    disk1_qty: int | None = None
    disk1_raid: str | None = Field(None, max_length=50)
    disk2_spec: str | None = Field(None, max_length=100)
    disk2_qty: int | None = None
    disk2_raid: str | None = Field(None, max_length=50)
    
    nic1: str | None = Field(None, max_length=100)
    nic2: str | None = Field(None, max_length=100)
    
    # Firmware
    bios_ver: str | None = Field(None, max_length=50)
    idrac_ver: str | None = Field(None, max_length=50)
    raid_ver: str | None = Field(None, max_length=50)
    
    address_id: int | None = None
    history: dict | None = None


class ServerInventoryCreate(ServerInventoryBase):
    pass


class ServerInventoryUpdate(BaseModel):
    serial_tag: str | None = Field(None, min_length=1, max_length=100)
    model: str | None = Field(None, min_length=1, max_length=100)
    vendor: str | None = Field(None, max_length=100)
    status: Literal["IN_STOCK", "RESERVED", "SCHEDULED", "DELIVERED", "RMA"] | None = None
    project_id: int | None = None
    in_date: date | None = None
    
    host_name: str | None = Field(None, max_length=100)
    service_ip: str | None = Field(None, max_length=50)
    mgmt_ip: str | None = Field(None, max_length=50)
    
    cpu_model: str | None = Field(None, max_length=100)
    cpu_core: int | None = None
    mem_capacity: int | None = None
    mem_gen: str | None = Field(None, max_length=50)
    mem_qty: int | None = None
    
    disk1_spec: str | None = Field(None, max_length=100)
    disk1_qty: int | None = None
    disk1_raid: str | None = Field(None, max_length=50)
    disk2_spec: str | None = Field(None, max_length=100)
    disk2_qty: int | None = None
    disk2_raid: str | None = Field(None, max_length=50)
    
    nic1: str | None = Field(None, max_length=100)
    nic2: str | None = Field(None, max_length=100)
    
    bios_ver: str | None = Field(None, max_length=50)
    idrac_ver: str | None = Field(None, max_length=50)
    raid_ver: str | None = Field(None, max_length=50)
    
    address_id: int | None = None
    history: dict | None = None


class ServerInventoryBulkCreate(BaseModel):
    """동일 사양 복사 다건 등록을 위한 스키마"""
    serial_tags: list[str] = Field(..., min_items=1)
    base_info: ServerInventoryCreate


class ServerInventoryOut(ServerInventoryBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
