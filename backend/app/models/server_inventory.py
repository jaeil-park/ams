"""
app/models/server_inventory.py — ServerInventory DB 모델
"""

from datetime import date
from sqlalchemy import Boolean, Date, ForeignKey, String, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class ServerInventory(Base, TimestampMixin):
    """서버 장비 재고 및 납품이력 테이블"""
    __tablename__ = "server_inventories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    serial_tag: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="SERVER", nullable=False)
    model: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    vendor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="IN_STOCK", nullable=False)  # IN_STOCK, RESERVED, SCHEDULED, DELIVERED, RMA
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    in_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # OS & Network
    host_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    service_ip: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mgmt_ip: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Specs
    cpu_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cpu_core: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mem_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mem_gen: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mem_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    disk1_spec: Mapped[str | None] = mapped_column(String(100), nullable=True)
    disk1_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    disk1_raid: Mapped[str | None] = mapped_column(String(50), nullable=True)
    disk2_spec: Mapped[str | None] = mapped_column(String(100), nullable=True)
    disk2_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    disk2_raid: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    nic1: Mapped[str | None] = mapped_column(String(100), nullable=True)
    nic2: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Firmware versions
    bios_ver: Mapped[str | None] = mapped_column(String(50), nullable=True)
    idrac_ver: Mapped[str | None] = mapped_column(String(50), nullable=True)
    raid_ver: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    address_id: Mapped[int | None] = mapped_column(ForeignKey("addresses.id"), nullable=True)
    history: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="server_inventories")
    warranties = relationship("Warranty", back_populates="server", cascade="all, delete-orphan")
