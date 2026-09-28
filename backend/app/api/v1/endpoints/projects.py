"""
app/api/v1/endpoints/projects.py — 프로젝트 API
"""

from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select, func, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Literal

from app import crud, models, schemas
from app.core.deps import get_db, get_current_user
from app.schemas.common import ResponseEnvelope, MetaSchema
from app.services import nas_docs
from app.services.audit import log_action
from app.services.completion_check import (
    blocking_reasons,
    evaluate_manual,
    run_auto_checks,
)

router = APIRouter()

# 프로젝트 진행상태 → 소속 서버 장비상태 연동 규칙.
# RMA 장비는 예외 처리가 필요한 별도 트랙이므로 어떤 경우에도 자동 변경하지 않는다.
_PROJECT_STATUS_TO_SERVER_STATUS = {
    "COMPLETED": "DELIVERED",
    "IN_PROGRESS": "SCHEDULED",
}


async def _project_ids_with_po(db: AsyncSession, project_ids: list[int]) -> set[int]:
    """전달한 프로젝트들 중 PO 문서가 첨부된 것들의 id 집합을 반환한다."""
    if not project_ids:
        return set()
    result = await db.execute(
        select(models.ProjectAttachment.project_id)
        .where(
            models.ProjectAttachment.project_id.in_(project_ids),
            models.ProjectAttachment.kind == "PO",
            models.ProjectAttachment.is_deleted == False,
        )
        .distinct()
    )
    return set(result.scalars().all())


async def _attach_has_po(db: AsyncSession, projects) -> None:
    """ProjectOut.has_po 에 실릴 값을 ORM 인스턴스에 얹는다 (DB에 저장되지 않는 파생 값)."""
    with_po = await _project_ids_with_po(db, [p.id for p in projects])
    for p in projects:
        p.has_po = p.id in with_po


async def _sync_server_status_with_project(
    db: AsyncSession, *, project_id: int, project_status: str
) -> int:
    """프로젝트 상태 변경 시 소속 서버들의 장비상태를 함께 맞춘다. 변경된 건수를 반환."""
    target_status = _PROJECT_STATUS_TO_SERVER_STATUS.get(project_status)
    if not target_status:
        return 0

    result = await db.execute(
        sa_update(models.ServerInventory)
        .where(
            models.ServerInventory.project_id == project_id,
            models.ServerInventory.is_deleted == False,
            models.ServerInventory.status != "RMA",
            models.ServerInventory.status != target_status,
        )
        .values(status=target_status)
        # 세션에 이미 로드된 ServerInventory 객체를 되돌아보지 않는 일괄 UPDATE.
        # 이 요청에서 그 객체들을 다시 쓰지 않으므로 동기화가 필요 없다.
        .execution_options(synchronize_session=False)
    )
    return result.rowcount or 0


@router.get("", response_model=ResponseEnvelope[list[schemas.project.ProjectOut]])
async def list_projects(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=1000),
    search: str | None = Query(None),
    status_filter: Literal["WAITING", "IN_PROGRESS", "COMPLETED"] | None = Query(None, alias="status"),
    customer_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """프로젝트 목록 조회 (검색 및 고객사 ID 필터 탑재)"""
    skip = (page - 1) * limit
    
    query = select(models.Project).where(models.Project.is_deleted == False)
    count_query = select(func.count(models.Project.id)).where(models.Project.is_deleted == False)
    
    if search:
        search_filter = models.Project.name.ilike(f"%{search}%") | models.Project.po_number.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
        
    if status_filter:
        query = query.where(models.Project.status == status_filter)
        count_query = count_query.where(models.Project.status == status_filter)
        
    if customer_id:
        query = query.where(models.Project.customer_id == customer_id)
        count_query = count_query.where(models.Project.customer_id == customer_id)
        
    query = query.order_by(models.Project.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    projects = result.scalars().all()
    await _attach_has_po(db, projects)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    total_pages = (total + limit - 1) // limit
    
    return ResponseEnvelope(
        data=projects,
        meta=MetaSchema(
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )
    )


@router.post("", response_model=ResponseEnvelope[schemas.project.ProjectOut], status_code=status.HTTP_201_CREATED)
async def create_project(
    obj_in: schemas.project.ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """신규 프로젝트 등록 (PO 번호 중복 조회)"""
    po_check = await db.execute(select(models.Project).where(
        models.Project.po_number == obj_in.po_number,
        models.Project.is_deleted == False
    ))
    if po_check.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 존재하는 PO 번호입니다."
        )
        
    # 고객사 유효성 검사
    cust = await crud.customer.get(db, id=obj_in.customer_id)
    if not cust:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 고객사 ID입니다."
        )
        
    new_project = await crud.project.create(db, obj_in=obj_in)
    await log_action(
        db,
        user_id=current_user.id,
        action="CREATE",
        resource_type="PROJECT",
        resource_id=new_project.id,
        after={"name": new_project.name, "po_number": new_project.po_number},
    )
    return ResponseEnvelope(data=new_project)


@router.get("/status-counts", response_model=ResponseEnvelope[dict[str, int]])
async def get_project_status_counts(
    search: str | None = Query(None),
    customer_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    진행상태별 건수 조회 (진행중/완료 탭의 건수 배지용).
    검색어·고객사 필터를 함께 넘기면 그 조건 안에서의 건수를 반환한다.
    """
    query = (
        select(models.Project.status, func.count(models.Project.id))
        .where(models.Project.is_deleted == False)
        .group_by(models.Project.status)
    )
    if search:
        query = query.where(
            models.Project.name.ilike(f"%{search}%") | models.Project.po_number.ilike(f"%{search}%")
        )
    if customer_id:
        query = query.where(models.Project.customer_id == customer_id)

    result = await db.execute(query)
    counts = {s: 0 for s in ("WAITING", "IN_PROGRESS", "COMPLETED")}
    for row_status, row_count in result.all():
        if row_status in counts:
            counts[row_status] = int(row_count or 0)
    counts["TOTAL"] = sum(counts.values())
    return ResponseEnvelope(data=counts)


@router.get("/{id}", response_model=ResponseEnvelope[schemas.project.ProjectOut])
async def get_project(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """프로젝트 상세 조회"""
    project = await crud.project.get(db, id=id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 프로젝트를 찾을 수 없습니다."
        )
    await _attach_has_po(db, [project])
    return ResponseEnvelope(data=project)


@router.patch("/{id}", response_model=ResponseEnvelope[schemas.project.ProjectOut])
async def update_project(
    id: int,
    obj_in: schemas.project.ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """프로젝트 수정 (PATCH 적용)"""
    project = await crud.project.get(db, id=id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 프로젝트를 찾을 수 없습니다."
        )
        
    if obj_in.customer_id is not None:
        cust = await crud.customer.get(db, id=obj_in.customer_id)
        if not cust:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="유효하지 않은 고객사 ID입니다."
            )
            
    before_state = {"name": project.name, "status": project.status}
    # 상태 값이 함께 전달되면 '바뀌었는지'와 무관하게 연동을 수행한다.
    # 전환 시점에만 돌리면, 기능 추가 이전에 이미 완료 처리된 프로젝트나
    # 완료 후에 추가된 서버가 영영 동기화되지 않는다 (멱등하게 맞추는 것이 안전하다).
    sync_target_status = obj_in.status if obj_in.status is not None else None

    # 완료 처리는 체크리스트를 모두 통과해야 한다.
    # (등록·진행중 단계에서는 막지 않는다. 이미 완료된 건의 재저장도 다시 검사하지 않는다)
    is_completing = sync_target_status == "COMPLETED" and project.status != "COMPLETED"
    if is_completing:
        checklist = obj_in.completion_checklist if obj_in.completion_checklist is not None else project.completion_checklist
        auto_checks = await run_auto_checks(db, project)
        manual_items = evaluate_manual(checklist)
        reasons = blocking_reasons(auto_checks, manual_items)
        if reasons:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="완료 처리 조건을 충족하지 않았습니다: " + ", ".join(reasons),
            )

    updated = await crud.project.update(db, db_obj=project, obj_in=obj_in)

    if is_completing:
        updated.completed_at = datetime.now()
        updated.completed_by = current_user.id
        db.add(updated)
        await db.commit()

    # 프로젝트 완료 처리 시 소속 서버도 납품완료로 연동 (진행중 → 납품예정)
    synced_count = 0
    if sync_target_status:
        synced_count = await _sync_server_status_with_project(
            db, project_id=id, project_status=sync_target_status
        )
        if synced_count:
            await db.commit()

    after_state = obj_in.model_dump(exclude_unset=True, mode="json")
    if synced_count:
        after_state["synced_servers"] = synced_count
    await log_action(
        db,
        user_id=current_user.id,
        action="UPDATE",
        resource_type="PROJECT",
        resource_id=id,
        before=before_state,
        after=after_state,
    )
    return ResponseEnvelope(data=updated)


@router.get("/{id}/completion-check", response_model=ResponseEnvelope[dict])
async def get_completion_check(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """완료 처리 체크리스트 조회 — 자동 검사 결과와 수기 확인 항목의 현재 상태."""
    project = await crud.project.get(db, id=id)
    if not project:
        raise HTTPException(status_code=404, detail="해당 프로젝트를 찾을 수 없습니다.")

    auto_checks = await run_auto_checks(db, project)
    manual_items = evaluate_manual(project.completion_checklist)
    return ResponseEnvelope(data={
        "auto_checks": auto_checks,
        "manual_items": manual_items,
        "blocking_reasons": blocking_reasons(auto_checks, manual_items),
        "completed_at": project.completed_at.isoformat() if project.completed_at else None,
    })


# ─── NAS 납품문서 폴더 (읽기 전용) ─────────────────────────────────────────

@router.get("/{id}/documents", response_model=ResponseEnvelope[dict])
async def list_project_documents(
    id: int,
    path: str | None = Query(None, description="프로젝트 폴더 기준 하위 경로"),
    relocate: bool = Query(False, description="true면 PO 번호로 폴더를 다시 찾는다"),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    프로젝트의 NAS 납품문서 폴더 내용을 조회한다 (읽기 전용).
    폴더 위치를 모르면 PO 번호로 찾아서 프로젝트에 기억해 둔다.
    """
    project = await crud.project.get(db, id=id)
    if not project:
        raise HTTPException(status_code=404, detail="해당 프로젝트를 찾을 수 없습니다.")

    if not nas_docs.is_enabled():
        return ResponseEnvelope(data={
            "enabled": False,
            "root": None,
            "path": None,
            "entries": [],
            "message": "NAS 문서 폴더가 연결되어 있지 않습니다.",
        })

    if relocate or not project.nas_path:
        # 자동 탐색은 최근 2개 연도만 (못 찾을 때 전 연도를 훑으면 매번 수 초가 걸린다).
        # 오래된 건은 사용자가 '다시 찾기'를 눌러 전체를 훑는다.
        found = nas_docs.find_project_folder(
            project.po_number, max_years=None if relocate else 2
        )
        if found and found != project.nas_path:
            project.nas_path = found
            db.add(project)
            await db.commit()
        elif not found:
            return ResponseEnvelope(data={
                "enabled": True,
                "root": None,
                "path": None,
                "entries": [],
                "message": f"PO 번호 '{project.po_number}'가 들어간 문서 폴더를 찾지 못했습니다.",
            })

    root = project.nas_path
    try:
        # 하위 경로는 항상 이 프로젝트 폴더 안쪽으로만 허용한다.
        # (문서 루트 하위인지만 보면 '..' 로 다른 고객사 폴더를 훑을 수 있다)
        target = nas_docs.resolve_within(root, path)
        entries = nas_docs.list_folder(target)
    except ValueError:
        raise HTTPException(status_code=400, detail="허용되지 않은 경로입니다.")
    except FileNotFoundError:
        return ResponseEnvelope(data={
            "enabled": True,
            "root": root,
            "path": None,
            "entries": [],
            "message": "기억해 둔 폴더가 더 이상 존재하지 않습니다. 다시 찾기를 눌러주세요.",
        })

    return ResponseEnvelope(data={
        "enabled": True,
        "root": root,
        "path": target,
        "entries": entries,
        "message": None,
    })


@router.get("/{id}/documents/download")
async def download_project_document(
    id: int,
    path: str = Query(..., description="문서 루트 기준 파일 경로"),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """NAS 문서 폴더의 파일을 내려받는다 (프로젝트 폴더 바깥은 접근 불가)."""
    project = await crud.project.get(db, id=id)
    if not project:
        raise HTTPException(status_code=404, detail="해당 프로젝트를 찾을 수 없습니다.")
    if not nas_docs.is_enabled() or not project.nas_path:
        raise HTTPException(status_code=404, detail="연결된 문서 폴더가 없습니다.")

    # 이 프로젝트의 폴더 안쪽 파일만 허용한다
    if not (path == project.nas_path or path.startswith(project.nas_path + "/")):
        raise HTTPException(status_code=403, detail="이 프로젝트의 문서가 아닙니다.")

    try:
        content, filename = nas_docs.read_file(path)
    except ValueError:
        raise HTTPException(status_code=400, detail="허용되지 않은 경로입니다.")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/{id}", response_model=ResponseEnvelope[schemas.project.ProjectOut])
async def delete_project(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """프로젝트 삭제 (Soft Delete 진행)"""
    project = await crud.project.get(db, id=id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 프로젝트를 찾을 수 없습니다."
        )
        
    deleted = await crud.project.remove(db, id=id)
    await log_action(
        db,
        user_id=current_user.id,
        action="DELETE",
        resource_type="PROJECT",
        resource_id=id,
        before={"name": project.name, "po_number": project.po_number},
    )
    return ResponseEnvelope(data=deleted)
