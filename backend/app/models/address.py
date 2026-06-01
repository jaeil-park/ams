"""
app/models/address.py — Address DB 모델
"""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Address(Base, TimestampMixin):
    """납품 주소 테이블"""
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    location: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    memo: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    customer = relationship("Customer", back_populates="addresses")
