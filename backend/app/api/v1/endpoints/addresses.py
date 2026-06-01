"""
app/api/v1/endpoints/addresses.py — 납품주소 API
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, models, schemas
from app.core.deps import get_db, get_current_user
from app.schemas.common import ResponseEnvelope

router = APIRouter()


@router.get("", response_model=ResponseEnvelope[list[schemas.address.AddressOut]])
async def list_addresses(
    customer_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """납품 주소 목록 조회 (고객사 ID 필터링 기본 탑재)"""
    query = select(models.Address)
    if customer_id:
        query = query.where(models.Address.customer_id == customer_id)
        
    result = await db.execute(query)
    addresses = result.scalars().all()
    
    return ResponseEnvelope(data=addresses)


@router.post("", response_model=ResponseEnvelope[schemas.address.AddressOut], status_code=status.HTTP_201_CREATED)
async def create_address(
    obj_in: schemas.address.AddressCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """신규 납품 주소 등록 (고객사 ID 적합성 사전 체크)"""
    customer = await crud.customer.get(db, id=obj_in.customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="존재하지 않는 고객사 ID입니다."
        )
        
    new_address = await crud.address.create(db, obj_in=obj_in)
    return ResponseEnvelope(data=new_address)


@router.patch("/{id}", response_model=ResponseEnvelope[schemas.address.AddressOut])
async def update_address(
    id: int,
    obj_in: schemas.address.AddressUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """납품 주소 정보 부분 수정"""
    address_obj = await crud.address.get(db, id=id)
    if not address_obj:
        raise HTTPException(status_code=404, detail="해당 납품 주소를 찾을 수 없습니다.")
        
    updated = await crud.address.update(db, db_obj=address_obj, obj_in=obj_in)
    return ResponseEnvelope(data=updated)


@router.delete("/{id}", response_model=ResponseEnvelope[schemas.address.AddressOut])
async def delete_address(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """납품 주소 레코드 삭제 (Hard Delete)"""
    address_obj = await crud.address.get(db, id=id)
    if not address_obj:
        raise HTTPException(status_code=404, detail="해당 납품 주소를 찾을 수 없습니다.")
        
    deleted = await crud.address.remove(db, id=id)
    return ResponseEnvelope(data=deleted)
