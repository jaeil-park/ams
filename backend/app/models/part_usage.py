"""
app/models/part_usage.py — PartUsage DB 모델
"""

from datetime import date
from sqlalchemy import Date, ForeignKey, String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class PartUsage(Base, TimestampMixin):
    """부품 출고/사용 이력 테이블"""
    __tablename__ = "part_usages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    part_id: Mapped[int] = mapped_column(ForeignKey("part_inventories.id", ondelete="CASCADE"), nullable=False)
    used_date: Mapped[date] = mapped_column(Date, nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    qty: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relationships
    part = relationship("PartInventory", back_populates="usages")
    customer = relationship("Customer")
