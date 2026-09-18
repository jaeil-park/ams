"""
app/schemas/attachment.py — 프로젝트 첨부파일 스키마

파일 바이트(data)는 어떤 응답에도 포함하지 않는다 — 실물은 전용 다운로드 경로로만 내려간다.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AttachmentOut(BaseModel):
    id: int
    project_id: int
    filename: str
    content_type: str | None = None
    size: int
    kind: str
    note: str | None = None
    uploaded_by: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttachmentUploadOut(BaseModel):
    """업로드 응답 — 첨부 정보와 함께, PO 문서에서 추출한 값과 불일치 항목을 돌려준다."""
    attachment: AttachmentOut
    parsed: dict | None = None
    mismatches: list[dict] = []
