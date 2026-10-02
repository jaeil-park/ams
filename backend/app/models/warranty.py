"""
app/models/warranty.py — Warranty DB 모델
"""

from datetime import date, datetime
from sqlalchemy import Date, DateTime, ForeignKey, String, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Warranty(Base, TimestampMixin):
    """서버 보증기간(워런티) 정보 테이블"""
    __tablename__ = "warranties"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("server_inventories.id", ondelete="CASCADE"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    # MANUAL(수기) / DELL_API(TechDirect) / DELL_WEB(Dell 사이트, 확장 프로그램) / HPE_WEB(HPE 포털 자동 조회)
    source: Mapped[str] = mapped_column(String(50), default="DELL", nullable=False)
    # 제조사 조회 시 종료일 기준이 된 지원 등급 (예: ProSupport, Wty: HPE HW Maintenance Onsite Support)
    service_level: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # 제조사 조회 원본 요약 (지원 항목별 시작/종료일 등)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_synced: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    server = relationship("ServerInventory", back_populates="warranties")
