"""
app/api/v1/endpoints/inventory.py — 서버 장비 재고 API (단건 등록 및 Bulk 복사 등록 지원)
"""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Literal

from app import crud, models, schemas
from app.core.deps import get_db, get_current_user
from app.schemas.common import ResponseEnvelope, MetaSchema
from app.services.audit import log_action

router = APIRouter()


@router.get("", response_model=ResponseEnvelope[list[schemas.inventory.ServerInventoryOut]])
async def list_inventory(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    status_filter: Literal["IN_STOCK", "RESERVED", "SCHEDULED", "DELIVERED", "RMA"] | None = Query(None, alias="status"),
    project_id: int | None = Query(None),
    location: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """서버 장비 재고 및 납품이력 목록 조회"""
    skip = (page - 1) * limit
    
    query = select(models.ServerInventory).where(models.ServerInventory.is_deleted == False)
    count_query = select(func.count(models.ServerInventory.id)).where(models.ServerInventory.is_deleted == False)
    
    if search:
        search_filter = (
            models.ServerInventory.serial_tag.ilike(f"%{search}%") | 
            models.ServerInventory.model.ilike(f"%{search}%") |
            models.ServerInventory.host_name.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
        
    if status_filter:
        query = query.where(models.ServerInventory.status == status_filter)
        count_query = count_query.where(models.ServerInventory.status == status_filter)
        
    if project_id:
        query = query.where(models.ServerInventory.project_id == project_id)
        count_query = count_query.where(models.ServerInventory.project_id == project_id)
        
    query = query.order_by(models.ServerInventory.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    servers = result.scalars().all()
    
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    total_pages = (total + limit - 1) // limit
    
    return ResponseEnvelope(
        data=servers,
        meta=MetaSchema(
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )
    )


@router.post("", response_model=ResponseEnvelope[schemas.inventory.ServerInventoryOut], status_code=status.HTTP_201_CREATED)
async def create_inventory(
    obj_in: schemas.inventory.ServerInventoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """단건 서버 입고 등록 (Serial Tag 중복 체크)"""
    serial_check = await db.execute(select(models.ServerInventory).where(
        models.ServerInventory.serial_tag == obj_in.serial_tag,
        models.ServerInventory.is_deleted == False
    ))
    if serial_check.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 존재하는 Serial Tag입니다."
        )
        
    # project_id 검증
    if obj_in.project_id:
        project = await crud.project.get(db, id=obj_in.project_id)
        if not project:
            raise HTTPException(status_code=400, detail="유효하지 않은 프로젝트 ID입니다.")
            
    # in_date 누락 시 오늘 날짜
    if not obj_in.in_date:
        obj_in.in_date = date.today()
        
    new_server = await crud.server_inventory.create(db, obj_in=obj_in)
    await log_action(
        db,
        user_id=current_user.id,
        action="CREATE",
        resource_type="SERVER",
        resource_id=new_server.id,
        after={"serial_tag": new_server.serial_tag, "model": new_server.model},
    )
    return ResponseEnvelope(data=new_server)


@router.post("/bulk", response_model=ResponseEnvelope[list[schemas.inventory.ServerInventoryOut]], status_code=status.HTTP_201_CREATED)
async def create_bulk_inventory(
    obj_in: schemas.inventory.ServerInventoryBulkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """동일사양 다건 입고 복사 등록 (각 S/N 마다 별도의 자산 레코드로 등록)"""
    created_servers = []
    
    # 1. 시리얼 태그 중복 여부 일괄 검증
    for serial in obj_in.serial_tags:
        serial_check = await db.execute(select(models.ServerInventory).where(
            models.ServerInventory.serial_tag == serial,
            models.ServerInventory.is_deleted == False
        ))
        if serial_check.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"중복된 Serial Tag가 포함되어 있습니다: {serial}"
            )
            
    # project_id 검증
    if obj_in.base_info.project_id:
        project = await crud.project.get(db, id=obj_in.base_info.project_id)
        if not project:
            raise HTTPException(status_code=400, detail="유효하지 않은 프로젝트 ID입니다.")

    base_data = obj_in.base_info.model_dump()
    if not base_data.get("in_date"):
        base_data["in_date"] = date.today()
        
    # 2. 다건 생성
    for serial in obj_in.serial_tags:
        item_data = base_data.copy()
        item_data["serial_tag"] = serial
        
        db_obj = models.ServerInventory(**item_data)
        db.add(db_obj)
        created_servers.append(db_obj)
        
    await db.commit()
    for s in created_servers:
        await db.refresh(s)

    await log_action(
        db,
        user_id=current_user.id,
        action="CREATE",
        resource_type="SERVER_BULK",
        resource_id=None,
        after={"count": len(created_servers), "serials": obj_in.serial_tags},
    )
    return ResponseEnvelope(data=created_servers)


@router.get("/{id}", response_model=ResponseEnvelope[schemas.inventory.ServerInventoryOut])
async def get_inventory(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """서버 장비 단건 상세 조회"""
    server = await crud.server_inventory.get(db, id=id)
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 서버 재고를 찾을 수 없습니다."
        )
    return ResponseEnvelope(data=server)


@router.patch("/{id}", response_model=ResponseEnvelope[schemas.inventory.ServerInventoryOut])
async def update_inventory(
    id: int,
    obj_in: schemas.inventory.ServerInventoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """서버 장비 사양 및 정보 수정"""
    server = await crud.server_inventory.get(db, id=id)
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 서버 재고를 찾을 수 없습니다."
        )
        
    if obj_in.project_id is not None:
        project = await crud.project.get(db, id=obj_in.project_id)
        if not project:
            raise HTTPException(status_code=400, detail="유효하지 않은 프로젝트 ID입니다.")
            
    before_state = {"serial_tag": server.serial_tag, "status": server.status, "project_id": server.project_id}
    updated = await crud.server_inventory.update(db, db_obj=server, obj_in=obj_in)
    await log_action(
        db,
        user_id=current_user.id,
        action="UPDATE",
        resource_type="SERVER",
        resource_id=id,
        before=before_state,
        after=obj_in.model_dump(exclude_unset=True),
    )
    return ResponseEnvelope(data=updated)


@router.delete("/{id}", response_model=ResponseEnvelope[schemas.inventory.ServerInventoryOut])
async def delete_inventory(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """서버 장비 삭제 (Soft Delete 처리)"""
    server = await crud.server_inventory.get(db, id=id)
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 서버 재고를 찾을 수 없습니다."
        )
        
    deleted = await crud.server_inventory.remove(db, id=id)
    await log_action(
        db,
        user_id=current_user.id,
        action="DELETE",
        resource_type="SERVER",
        resource_id=id,
        before={"serial_tag": server.serial_tag, "model": server.model},
    )
    return ResponseEnvelope(data=deleted)
