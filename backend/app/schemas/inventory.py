"""
app/schemas/inventory.py — ServerInventory Pydantic v2 스키마
"""

from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Literal


class _BlankToNoneMixin(BaseModel):
    """
    HTML 폼은 비워 둔 숫자/날짜 입력을 빈 문자열("")로 전송한다.
    이를 그대로 검증하면 int_parsing / date_parsing 422가 발생하므로 None으로 정규화한다.
    """

    @field_validator("*", mode="before")
    @classmethod
    def _blank_to_none(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v


class ServerInventoryBase(_BlankToNoneMixin):
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
    disk3_spec: str | None = Field(None, max_length=100)
    disk3_qty: int | None = None
    disk3_raid: str | None = Field(None, max_length=50)
    disk4_spec: str | None = Field(None, max_length=100)
    disk4_qty: int | None = None
    disk4_raid: str | None = Field(None, max_length=50)
    disk5_spec: str | None = Field(None, max_length=100)
    disk5_qty: int | None = None
    disk5_raid: str | None = Field(None, max_length=50)

    nic1: str | None = Field(None, max_length=100)
    nic2: str | None = Field(None, max_length=100)
    extra_parts: list[dict] | None = None

    # Firmware
    bios_ver: str | None = Field(None, max_length=50)
    idrac_ver: str | None = Field(None, max_length=50)
    raid_ver: str | None = Field(None, max_length=50)

    address_id: int | None = None
    history: dict | None = None
    notes: str | None = Field(None, max_length=2000)


class ServerInventoryCreate(ServerInventoryBase):
    pass


class ServerInventoryUpdate(_BlankToNoneMixin):
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
    disk3_spec: str | None = Field(None, max_length=100)
    disk3_qty: int | None = None
    disk3_raid: str | None = Field(None, max_length=50)
    disk4_spec: str | None = Field(None, max_length=100)
    disk4_qty: int | None = None
    disk4_raid: str | None = Field(None, max_length=50)
    disk5_spec: str | None = Field(None, max_length=100)
    disk5_qty: int | None = None
    disk5_raid: str | None = Field(None, max_length=50)

    nic1: str | None = Field(None, max_length=100)
    nic2: str | None = Field(None, max_length=100)
    extra_parts: list[dict] | None = None

    bios_ver: str | None = Field(None, max_length=50)
    idrac_ver: str | None = Field(None, max_length=50)
    raid_ver: str | None = Field(None, max_length=50)

    address_id: int | None = None
    history: dict | None = None
    notes: str | None = Field(None, max_length=2000)


class ServerInventoryBulkCreate(BaseModel):
    """동일 사양 복사 다건 등록을 위한 스키마"""
    serial_tags: list[str] = Field(..., min_items=1)
    base_info: ServerInventoryCreate


class ServerInventoryOut(ServerInventoryBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
