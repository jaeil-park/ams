"""
app/models/part_inventory.py — PartInventory DB 모델
"""

from datetime import date
from sqlalchemy import Boolean, Date, ForeignKey, String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class PartInventory(Base, TimestampMixin):
    """부품(파트) 재고 테이블"""
    __tablename__ = "part_inventories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(50), default="PART", nullable=False)
    model: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    qty: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="IN_STOCK", nullable=False)  # IN_STOCK, RMA, etc.
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    warranty_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="part_inventories")
    usages = relationship("PartUsage", back_populates="part", cascade="all, delete-orphan")
