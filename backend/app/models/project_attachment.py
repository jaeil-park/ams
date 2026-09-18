"""
app/models/project_attachment.py — 프로젝트 첨부파일 DB 모델

파일 실물을 DB(BYTEA)에 보관한다.
- 백엔드 컨테이너에 별도 볼륨을 마운트하지 않아도 되고, 스택을 재배포해도 파일이 남는다.
- 기존 PostgreSQL 백업에 함께 포함된다.
- 대신 대용량에는 부적합하므로 업로드 시 파일당 크기 상한(MAX_ATTACHMENT_BYTES)을 강제한다.
"""

from sqlalchemy import Boolean, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class ProjectAttachment(Base, TimestampMixin):
    """프로젝트 첨부파일 (PO, 견적서, 검수확인서 등)"""
    __tablename__ = "project_attachments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id"), index=True, nullable=False
    )

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(150), nullable=True)
    size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # PO / QUOTE / INSPECTION / OTHER
    kind: Mapped[str] = mapped_column(String(30), nullable=False, default="OTHER")
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    uploaded_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    project = relationship("Project", back_populates="attachments")
