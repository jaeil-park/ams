"""
app/models/project.py — Project DB 모델
"""

from datetime import date
from sqlalchemy import Boolean, Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Project(Base, TimestampMixin):
    """프로젝트 테이블"""
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    po_number: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    manager: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="WAITING", nullable=False)  # WAITING, IN_PROGRESS, COMPLETED
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # 실제 납품일정

    # ─── PO 문서 기준값 ────────────────────────────────────────────────────
    # PO 첨부 시 문서에서 읽어 저장한다. 위쪽 필드(실제값)와 별도로 보관하는 이유는,
    # 실제 납품이 PO대로 이루어지지 않는 경우가 정상적으로 존재하기 때문이다.
    # 둘을 나란히 두어야 "PO는 2대인데 1대만 납품" 같은 상황을 있는 그대로 기록할 수 있다.
    po_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    po_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    po_delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    po_variance_note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    customer = relationship("Customer", back_populates="projects")
    server_inventories = relationship("ServerInventory", back_populates="project")
    part_inventories = relationship("PartInventory", back_populates="project")
    attachments = relationship(
        "ProjectAttachment", back_populates="project", cascade="all, delete-orphan"
    )
