"""
app/api/v1/endpoints/customers.py — 고객사 API
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


@router.get("", response_model=ResponseEnvelope[list[schemas.customer.CustomerOut]])
async def list_customers(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    status_filter: Literal["ACTIVE", "INACTIVE"] | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """고객사 목록 조회 (검색, 필터, 페이지네이션 및 Soft Delete 필터 탑재)"""
    skip = (page - 1) * limit
    
    # 쿼리 빌드
    query = select(models.Customer).where(models.Customer.is_deleted == False)
    count_query = select(func.count(models.Customer.id)).where(models.Customer.is_deleted == False)
    
    if search:
        search_filter = models.Customer.name.ilike(f"%{search}%") | models.Customer.code.ilike(f"%{search}%")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
        
    if status_filter:
        query = query.where(models.Customer.status == status_filter)
        count_query = count_query.where(models.Customer.status == status_filter)
        
    query = query.order_by(models.Customer.created_at.desc()).offset(skip).limit(limit)
    
    # 실행
    result = await db.execute(query)
    customers = result.scalars().all()
    
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    total_pages = (total + limit - 1) // limit
    
    return ResponseEnvelope(
        data=customers,
        meta=MetaSchema(
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )
    )


@router.post("", response_model=ResponseEnvelope[schemas.customer.CustomerOut], status_code=status.HTTP_201_CREATED)
async def create_customer(
    obj_in: schemas.customer.CustomerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """신규 고객사 등록 (코드 중복검사 수행)"""
    code_check = await db.execute(select(models.Customer).where(
        models.Customer.code == obj_in.code,
        models.Customer.is_deleted == False
    ))
    if code_check.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 존재하는 고객사 코드입니다."
        )

    new_customer = await crud.customer.create(db, obj_in=obj_in)
    await log_action(
        db,
        user_id=current_user.id,
        action="CREATE",
        resource_type="CUSTOMER",
        resource_id=new_customer.id,
        after=obj_in.model_dump(),
    )
    return ResponseEnvelope(data=new_customer)


@router.get("/{id}", response_model=ResponseEnvelope[schemas.customer.CustomerOut])
async def get_customer(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """고객사 단건 상세 조회"""
    customer = await crud.customer.get(db, id=id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 고객사를 찾을 수 없습니다."
        )
    return ResponseEnvelope(data=customer)


@router.patch("/{id}", response_model=ResponseEnvelope[schemas.customer.CustomerOut])
async def update_customer(
    id: int,
    obj_in: schemas.customer.CustomerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """고객사 정보 수정 (PATCH를 사용한 부분 수정)"""
    customer = await crud.customer.get(db, id=id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 고객사를 찾을 수 없습니다."
        )

    before_state = {"name": customer.name, "status": customer.status, "manager": customer.manager}
    updated = await crud.customer.update(db, db_obj=customer, obj_in=obj_in)
    await log_action(
        db,
        user_id=current_user.id,
        action="UPDATE",
        resource_type="CUSTOMER",
        resource_id=id,
        before=before_state,
        after=obj_in.model_dump(exclude_unset=True),
    )
    return ResponseEnvelope(data=updated)


@router.delete("/{id}", response_model=ResponseEnvelope[schemas.customer.CustomerOut])
async def delete_customer(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """고객사 삭제 (Soft Delete 진행)"""
    customer = await crud.customer.get(db, id=id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 고객사를 찾을 수 없습니다."
        )

    deleted = await crud.customer.remove(db, id=id)
    await log_action(
        db,
        user_id=current_user.id,
        action="DELETE",
        resource_type="CUSTOMER",
        resource_id=id,
        before={"name": customer.name, "code": customer.code},
    )
    return ResponseEnvelope(data=deleted)
