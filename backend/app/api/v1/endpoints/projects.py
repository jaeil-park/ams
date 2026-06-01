"""
app/api/v1/endpoints/projects.py — 프로젝트 API
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Literal

from app import crud, models, schemas
from app.core.deps import get_db, get_current_user
from app.schemas.common import ResponseEnvelope, MetaSchema
from app.services.audit import log_action

router = APIRouter()


@router.get("", response_model=ResponseEnvelope[list[schemas.project.ProjectOut]])
async def list_projects(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
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
    updated = await crud.project.update(db, db_obj=project, obj_in=obj_in)
    await log_action(
        db,
        user_id=current_user.id,
        action="UPDATE",
        resource_type="PROJECT",
        resource_id=id,
        before=before_state,
        after=obj_in.model_dump(exclude_unset=True),
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
