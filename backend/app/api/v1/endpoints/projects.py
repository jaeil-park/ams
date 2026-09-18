"""
app/api/v1/endpoints/projects.py — 프로젝트 API
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Literal

from app import crud, models, schemas
from app.core.deps import get_db, get_current_user
from app.schemas.common import ResponseEnvelope, MetaSchema
from app.services.audit import log_action

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

    # PO 문서는 필수 첨부다 — 완료 처리 시점에는 반드시 있어야 한다.
    # (등록 시점에는 PO가 아직 도착하지 않았을 수 있으므로 그때는 막지 않는다)
    if sync_target_status == "COMPLETED" and project.status != "COMPLETED":
        if not await _project_ids_with_po(db, [id]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PO 문서가 첨부되지 않아 완료 처리할 수 없습니다. "
                       "PO 번호를 클릭해 상세 화면에서 PO 문서를 먼저 첨부해 주세요.",
            )

    updated = await crud.project.update(db, db_obj=project, obj_in=obj_in)

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
