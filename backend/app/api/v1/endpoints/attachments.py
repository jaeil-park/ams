"""
app/api/v1/endpoints/attachments.py — 프로젝트 첨부파일 API

- POST   /projects/{project_id}/attachments  업로드 (PO HTML이면 내용 자동 추출)
- GET    /projects/{project_id}/attachments  목록 조회 (파일 실물 제외)
- GET    /attachments/{id}/download          원본 다운로드
- DELETE /attachments/{id}                   삭제 (Soft Delete)

보안: 업로드된 HTML은 절대 앱과 같은 출처에서 렌더링하지 않는다.
다운로드는 항상 Content-Disposition: attachment + 안전한 content-type으로 내려보내
브라우저가 문서로 실행하지 않도록 한다.
"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, models, schemas
from app.core.deps import get_db, get_current_user
from app.schemas.common import ResponseEnvelope
from app.services.audit import log_action
from app.services.po_parser import is_parsable_po, parse_ariba_po

router = APIRouter()

MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024  # 10MB
ALLOWED_KINDS = ("PO", "QUOTE", "INSPECTION", "OTHER")

# 브라우저가 실행/렌더링할 수 있는 형식은 다운로드 시 중립 타입으로 바꿔 내려보낸다.
_SAFE_DOWNLOAD_TYPE = "application/octet-stream"


async def _get_attachment(db: AsyncSession, attachment_id: int) -> models.ProjectAttachment:
    result = await db.execute(
        select(models.ProjectAttachment).where(
            models.ProjectAttachment.id == attachment_id,
            models.ProjectAttachment.is_deleted == False,
        )
    )
    attachment = result.scalars().first()
    if not attachment:
        raise HTTPException(status_code=404, detail="첨부파일을 찾을 수 없습니다.")
    return attachment


def _diff_against_project(project: models.Project, parsed: dict) -> list[dict]:
    """PO에서 추출한 값과 등록된 프로젝트 값을 비교해 다른 항목만 돌려준다."""
    checks = [
        ("po_number", "PO 번호", project.po_number),
        ("delivery_date", "납품일정", project.scheduled_date.isoformat() if project.scheduled_date else None),
        ("requester_email", "담당자 이메일", project.email),
        ("ship_to_address", "납품 위치", project.location),
    ]
    mismatches = []
    for key, label, current in checks:
        po_value = parsed.get(key)
        if not po_value:
            continue
        if not current:
            mismatches.append({"field": key, "label": label, "po_value": po_value, "current": None})
        elif str(current).strip() != str(po_value).strip():
            mismatches.append({"field": key, "label": label, "po_value": po_value, "current": str(current)})
    return mismatches


@router.post(
    "/projects/{project_id}/attachments",
    response_model=ResponseEnvelope[schemas.attachment.AttachmentUploadOut],
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    project_id: int,
    file: UploadFile = File(...),
    kind: str = Form("OTHER"),
    note: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """프로젝트에 파일을 첨부한다. PO HTML이면 주요 항목을 자동 추출해 함께 돌려준다."""
    project = await crud.project.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="해당 프로젝트를 찾을 수 없습니다.")

    if kind not in ALLOWED_KINDS:
        raise HTTPException(
            status_code=400,
            detail=f"유효하지 않은 첨부 구분입니다. ({', '.join(ALLOWED_KINDS)} 중 하나)",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="빈 파일은 업로드할 수 없습니다.")
    if len(raw) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"파일 크기가 너무 큽니다. (최대 {MAX_ATTACHMENT_BYTES // (1024 * 1024)}MB)",
        )

    attachment = models.ProjectAttachment(
        project_id=project_id,
        filename=file.filename or "unnamed",
        content_type=file.content_type,
        size=len(raw),
        kind=kind,
        note=note,
        data=raw,
        uploaded_by=current_user.id,
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)

    parsed = None
    mismatches: list[dict] = []
    if kind == "PO" and is_parsable_po(attachment.filename, attachment.content_type):
        parsed = parse_ariba_po(raw) or None
        if parsed:
            mismatches = _diff_against_project(project, parsed)

    await log_action(
        db,
        user_id=current_user.id,
        action="CREATE",
        resource_type="PROJECT_ATTACHMENT",
        resource_id=attachment.id,
        after={"project_id": project_id, "filename": attachment.filename, "kind": kind, "size": attachment.size},
    )

    return ResponseEnvelope(
        data=schemas.attachment.AttachmentUploadOut(
            attachment=schemas.attachment.AttachmentOut.model_validate(attachment),
            parsed=parsed,
            mismatches=mismatches,
        )
    )


@router.get(
    "/projects/{project_id}/attachments",
    response_model=ResponseEnvelope[list[schemas.attachment.AttachmentOut]],
)
async def list_attachments(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """프로젝트 첨부파일 목록 조회 (파일 실물은 포함하지 않음)"""
    result = await db.execute(
        select(models.ProjectAttachment)
        .where(
            models.ProjectAttachment.project_id == project_id,
            models.ProjectAttachment.is_deleted == False,
        )
        .order_by(models.ProjectAttachment.created_at.desc())
    )
    return ResponseEnvelope(data=result.scalars().all())


@router.get("/attachments/{id}/download")
async def download_attachment(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """첨부파일 원본 다운로드 (브라우저에서 렌더링되지 않도록 항상 다운로드로 내려보냄)"""
    attachment = await _get_attachment(db, id)
    filename = quote(attachment.filename)
    return Response(
        content=attachment.data,
        media_type=_SAFE_DOWNLOAD_TYPE,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get(
    "/attachments/{id}/parsed",
    response_model=ResponseEnvelope[dict],
)
async def get_attachment_parsed(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """저장된 PO 문서를 다시 파싱해 추출 항목을 돌려준다 (원본 HTML은 내보내지 않음)."""
    attachment = await _get_attachment(db, id)
    if not is_parsable_po(attachment.filename, attachment.content_type):
        raise HTTPException(status_code=400, detail="내용을 추출할 수 있는 PO 문서가 아닙니다.")

    parsed = parse_ariba_po(attachment.data)
    if not parsed:
        raise HTTPException(
            status_code=400,
            detail="이 문서에서는 PO 항목을 인식하지 못했습니다. (Ariba 발행 PO만 지원)",
        )

    project = await crud.project.get(db, id=attachment.project_id)
    return ResponseEnvelope(
        data={
            "parsed": parsed,
            "mismatches": _diff_against_project(project, parsed) if project else [],
        }
    )


@router.delete("/attachments/{id}", response_model=ResponseEnvelope[schemas.attachment.AttachmentOut])
async def delete_attachment(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """첨부파일 삭제 (Soft Delete)"""
    attachment = await _get_attachment(db, id)
    attachment.is_deleted = True
    db.add(attachment)
    await db.commit()

    await log_action(
        db,
        user_id=current_user.id,
        action="DELETE",
        resource_type="PROJECT_ATTACHMENT",
        resource_id=id,
        before={"project_id": attachment.project_id, "filename": attachment.filename},
    )
    return ResponseEnvelope(data=attachment)
