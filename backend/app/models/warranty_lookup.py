"""
app/models/warranty_lookup.py — 제조사 워런티 조회 요청(대기열) / 조회 작업자 상태 모델

- WarrantyLookup: 시리얼 1건 = 1행. 같은 요청에서 만든 행은 batch_id 로 묶인다.
    DELL  → Dell TechDirect API 키가 있으면 백엔드가 즉시 처리, 없으면 WAITING_EXTENSION
            (브라우저 확장 프로그램이 Dell 사이트에서 조회 후 결과를 올려 준다)
    HPE   → PENDING 으로 두면 warranty-worker 컨테이너가 HPE 포털에서 조회한다
- WarrantyWorkerStatus: 작업자(HPE 자동 조회 등)의 마지막 응답 시각과 로그인 상태
"""

from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class WarrantyLookup(Base, TimestampMixin):
    """제조사 워런티 조회 요청 (시리얼 단위)"""
    __tablename__ = "warranty_lookups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    serial_tag: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    vendor: Mapped[str] = mapped_column(String(20), nullable=False)  # DELL / HPE / UNKNOWN
    # PENDING / RUNNING / WAITING_EXTENSION / DONE / NOT_FOUND / ERROR
    status: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    inventory_id: Mapped[int | None] = mapped_column(ForeignKey("server_inventories.id"), nullable=True)
    apply_to_inventory: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    service_level: Mapped[str | None] = mapped_column(String(200), nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    requested_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    # 조회 기록 삭제는 숨김 처리 (claude_rule.md §5 Soft Delete). 대기 중 건을 삭제하면 조회도 취소된다.
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)


class WarrantyWorkerStatus(Base, TimestampMixin):
    """워런티 조회 작업자 상태 (name 단위 1행, 예: HPE)"""
    __tablename__ = "warranty_worker_statuses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    state: Mapped[str] = mapped_column(String(30), nullable=False)  # READY / BUSY / LOGIN_REQUIRED / ERROR
    message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
