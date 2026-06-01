"""
app/api/v1/endpoints/parts.py — 부품(파트) 재고 및 사용이력 API
- 일반 파트 정보 조회, 신규 파트 추가, 파트 출고/사용 내역(Usage) 등록을 지원합니다.
- 파트 수량 강제 수정(ADMIN 승인 워크플로우 연동)을 지원합니다.
"""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, models, schemas
from app.core.deps import get_db, get_current_user, require_admin
from app.schemas.common import ResponseEnvelope, MetaSchema

router = APIRouter()


@router.get("", response_model=ResponseEnvelope[list[schemas.part.PartInventoryOut]])
async def list_parts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """파트 재고 목록 조회"""
    skip = (page - 1) * limit
    
    query = select(models.PartInventory).where(models.PartInventory.is_deleted == False)
    count_query = select(func.count(models.PartInventory.id)).where(models.PartInventory.is_deleted == False)
    
    if search:
        search_filter = models.PartInventory.model.ilike(f"%{search}%") | models.PartInventory.location.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
        
    query = query.order_by(models.PartInventory.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    parts = result.scalars().all()
    
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    total_pages = (total + limit - 1) // limit
    
    return ResponseEnvelope(
        data=parts,
        meta=MetaSchema(
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )
    )


@router.post("", response_model=ResponseEnvelope[schemas.part.PartInventoryOut], status_code=status.HTTP_201_CREATED)
async def create_part(
    obj_in: schemas.part.PartInventoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """신규 파트 추가 (워런티 자동 계산: 구매일 + 365일)"""
    if obj_in.purchase_date and not obj_in.warranty_end:
        # 비즈니스 로직 §3: 파트 워런티 자동 계산 (구매일 + 365일)
        from datetime import timedelta
        obj_in.warranty_end = obj_in.purchase_date + timedelta(days=365)
        
    new_part = await crud.part_inventory.create(db, obj_in=obj_in)
    return ResponseEnvelope(data=new_part)


@router.get("/{id}", response_model=ResponseEnvelope[schemas.part.PartInventoryOut])
async def get_part(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """특정 파트 단건 조회"""
    part = await crud.part_inventory.get(db, id=id)
    if not part:
        raise HTTPException(status_code=404, detail="해당 파트 재고를 찾을 수 없습니다.")
    return ResponseEnvelope(data=part)


@router.post("/{id}/usage", response_model=ResponseEnvelope[schemas.part.PartUsageOut], status_code=status.HTTP_201_CREATED)
async def create_part_usage(
    id: int,
    obj_in: schemas.part.PartUsageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """파트 사용(출고) 내역 등록 (등록 시 파트 수량이 자동 감소합니다)"""
    part = await crud.part_inventory.get(db, id=id)
    if not part:
        raise HTTPException(status_code=404, detail="해당 파트를 찾을 수 없습니다.")
        
    if part.qty < obj_in.qty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"출고 수량이 재고 수량보다 많습니다. (현재 재고: {part.qty})"
        )
        
    # 고객사 검증
    cust = await crud.customer.get(db, id=obj_in.customer_id)
    if not cust:
        raise HTTPException(status_code=400, detail="유효하지 않은 고객사 ID입니다.")
        
    # 파트 수량 차감
    part.qty -= obj_in.qty
    db.add(part)
    
    # 내역 생성
    new_usage = models.PartUsage(
        part_id=id,
        used_date=obj_in.used_date or date.today(),
        customer_id=obj_in.customer_id,
        location=obj_in.location,
        reason=obj_in.reason,
        qty=obj_in.qty
    )
    db.add(new_usage)
    await db.commit()
    await db.refresh(new_usage)
    
    return ResponseEnvelope(data=new_usage)


@router.patch("/{id}/qty", response_model=ResponseEnvelope[schemas.part.ApprovalOut], status_code=status.HTTP_202_ACCEPTED)
async def request_part_qty_update(
    id: int,
    target_qty: int = Query(..., ge=0),
    reason: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    [핵심 비즈니스 로직 §4] 파트 수량 강제 수정
    - 직접 수정되지 않고, 결재 테이블(approvals)에 PENDING 상태로 결재 요청이 예약됩니다.
    - ADMIN이 승인해 주어야만 최종 반영이 완료됩니다.
    """
    part = await crud.part_inventory.get(db, id=id)
    if not part:
        raise HTTPException(status_code=404, detail="해당 파트를 찾을 수 없습니다.")
        
    # 결재 승인 대기 레코드 생성
    approval_req = models.Approval(
        requester_id=current_user.id,
        resource_type="PART_QTY",
        resource_id=id,
        status="PENDING",
        reason=reason,
        payload={"qty": target_qty}
    )
    db.add(approval_req)
    await db.commit()
    await db.refresh(approval_req)
    
    return ResponseEnvelope(data=approval_req)
