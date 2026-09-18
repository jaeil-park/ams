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

from datetime import date
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
# PO=구매오더, QUOTE=견적서, INSPECTION=검수확인서, HANDOVER=인수인계서, OTHER=기타
ALLOWED_KINDS = ("PO", "QUOTE", "INSPECTION", "HANDOVER", "OTHER")

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


# PO 문서가 원본인 항목 — 첨부 시 자동으로 덮어쓴다.
# 선지원 후 PO가 발행되는 경우, 임시로 적어둔 PO 번호를 실제 번호로 정정하는 것이 목적이다.
# 실제 진행값(납품일정 등)은 여기 포함하지 않는다 — PO대로 납품되지 않는 경우가 정상적으로 있다.
_OPTIONAL_FIELDS = [
    # (parsed 키, 프로젝트 필드, 라벨, 설명)
    ("delivery_date", "scheduled_date", "실제 납품일정", "PO 요구 납기에 맞출 때만 선택하세요"),
    ("requester", "manager", "담당자", None),
    ("requester_email", "email", "담당자 이메일", None),
    ("ship_to_address", "location", "납품 위치", None),
    ("item_description", "name", "프로젝트명", "PO 품목명으로 바꿀 때만 선택하세요"),
]


def _current_value(project: models.Project, field: str) -> str | None:
    value = getattr(project, field, None)
    if value is None:
        return None
    return value.isoformat() if isinstance(value, date) else str(value)


def _build_optional_choices(project: models.Project, parsed: dict) -> list[dict]:
    """PO 값과 실제값이 다른 선택 항목만 돌려준다 (사용자가 고를 대상)."""
    choices = []
    for parsed_key, field, label, hint in _OPTIONAL_FIELDS:
        po_value = parsed.get(parsed_key)
        if not po_value:
            continue
        current = _current_value(project, field)
        if current and current.strip() == str(po_value).strip():
            continue
        choices.append({
            "field": field,
            "label": label,
            "hint": hint,
            "po_value": str(po_value),
            "current": current,
        })
    return choices


async def _merge_po_into_project(
    db: AsyncSession, project: models.Project, parsed: dict
) -> tuple[list[dict], list[str]]:
    """
    PO 문서 내용을 프로젝트에 병합한다.
    필수(PO가 원본) 항목만 자동으로 덮어쓰고, 자동 반영한 항목과 경고를 돌려준다.
    """
    auto_applied: list[dict] = []
    warnings: list[str] = []

    # 1) PO 번호 — 선지원 후 PO 발행 시 임시 번호를 실제 번호로 정정
    po_number = parsed.get("po_number")
    if po_number and po_number != project.po_number:
        duplicate = await db.execute(
            select(models.Project).where(
                models.Project.po_number == po_number,
                models.Project.id != project.id,
                models.Project.is_deleted == False,
            )
        )
        if duplicate.scalars().first():
            warnings.append(
                f"PO 번호 '{po_number}'가 이미 다른 프로젝트에 등록되어 있어 자동 반영하지 않았습니다. "
                "중복 등록이 아닌지 확인해 주세요."
            )
        else:
            auto_applied.append({
                "field": "po_number", "label": "PO 번호",
                "before": project.po_number, "after": po_number,
            })
            project.po_number = po_number

    # 2) PO 기준 금액
    if parsed.get("total_amount") is not None and project.po_amount != parsed["total_amount"]:
        auto_applied.append({
            "field": "po_amount", "label": "PO 금액",
            "before": project.po_amount, "after": parsed["total_amount"],
        })
        project.po_amount = parsed["total_amount"]
        project.po_currency = parsed.get("currency")

    # 3) PO 기준 요구 납기 (실제 납품일정과는 별도로 보관)
    if parsed.get("delivery_date"):
        try:
            po_date = date.fromisoformat(parsed["delivery_date"])
        except ValueError:
            po_date = None
        if po_date and project.po_delivery_date != po_date:
            auto_applied.append({
                "field": "po_delivery_date", "label": "PO 요구 납기",
                "before": project.po_delivery_date.isoformat() if project.po_delivery_date else None,
                "after": po_date.isoformat(),
            })
            project.po_delivery_date = po_date

    if auto_applied:
        db.add(project)
        await db.commit()
        await db.refresh(project)

    return auto_applied, warnings


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
    auto_applied: list[dict] = []
    optional: list[dict] = []
    warnings: list[str] = []
    if kind == "PO" and is_parsable_po(attachment.filename, attachment.content_type):
        parsed = parse_ariba_po(raw) or None
        if parsed:
            auto_applied, warnings = await _merge_po_into_project(db, project, parsed)
            optional = _build_optional_choices(project, parsed)

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
            auto_applied=auto_applied,
            optional=optional,
            warnings=warnings,
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
    response_model=ResponseEnvelope[schemas.attachment.PoMergeResult],
)
async def get_attachment_parsed(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    저장된 PO 문서를 다시 읽어 추출 항목과 선택 반영 후보를 돌려준다.
    조회 전용이므로 프로젝트 값을 변경하지 않는다 (원본 HTML도 내보내지 않음).
    """
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
        data=schemas.attachment.PoMergeResult(
            parsed=parsed,
            optional=_build_optional_choices(project, parsed) if project else [],
        )
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
