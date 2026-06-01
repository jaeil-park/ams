"""
app/db/base.py — SQLAlchemy DeclarativeBase + 공통 컬럼 Mixin
테이블명: 복수형 snake_case (claude_rule.md §5)
공통 컬럼: created_at, updated_at 자동 설정
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """모든 ORM 모델의 공통 베이스 클래스"""
    pass


class TimestampMixin:
    """created_at / updated_at 자동 관리 Mixin"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
