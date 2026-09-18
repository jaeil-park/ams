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


class PoMergeResult(BaseModel):
    """
    PO 문서 병합 결과.

    - auto_applied: PO가 원본인 필수 항목 — 자동으로 덮어썼다.
    - optional: 실제 진행값이라 PO와 달라도 되는 항목 — 사용자가 고르게 남겨둔다.
    - warnings: 자동 반영을 건너뛴 사유 등 확인이 필요한 안내.
    """
    parsed: dict | None = None
    auto_applied: list[dict] = []
    optional: list[dict] = []
    warnings: list[str] = []


class AttachmentUploadOut(PoMergeResult):
    """업로드 응답 — 첨부 정보와 PO 병합 결과."""
    attachment: AttachmentOut
