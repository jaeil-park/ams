"""
app/api/v1/endpoints/contacts.py — 고객사 담당자 API
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, models, schemas
from app.core.deps import get_db, get_current_user
from app.schemas.common import ResponseEnvelope

router = APIRouter()


@router.get("", response_model=ResponseEnvelope[list[schemas.customer_contact.CustomerContactOut]])
async def list_contacts(
    customer_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """고객사 담당자 목록 조회 (고객사 ID 필터링 기본 탑재)"""
    query = select(models.CustomerContact)
    if customer_id:
        query = query.where(models.CustomerContact.customer_id == customer_id)

    result = await db.execute(query)
    contacts = result.scalars().all()

    return ResponseEnvelope(data=contacts)


@router.post("", response_model=ResponseEnvelope[schemas.customer_contact.CustomerContactOut], status_code=status.HTTP_201_CREATED)
async def create_contact(
    obj_in: schemas.customer_contact.CustomerContactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """신규 고객사 담당자 등록 (고객사 ID 적합성 사전 체크)"""
    customer = await crud.customer.get(db, id=obj_in.customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="존재하지 않는 고객사 ID입니다."
        )

    new_contact = await crud.customer_contact.create(db, obj_in=obj_in)
    return ResponseEnvelope(data=new_contact)


@router.patch("/{id}", response_model=ResponseEnvelope[schemas.customer_contact.CustomerContactOut])
async def update_contact(
    id: int,
    obj_in: schemas.customer_contact.CustomerContactUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """고객사 담당자 정보 부분 수정"""
    contact = await crud.customer_contact.get(db, id=id)
    if not contact:
        raise HTTPException(status_code=404, detail="해당 담당자를 찾을 수 없습니다.")

    updated = await crud.customer_contact.update(db, db_obj=contact, obj_in=obj_in)
    return ResponseEnvelope(data=updated)


@router.delete("/{id}", response_model=ResponseEnvelope[schemas.customer_contact.CustomerContactOut])
async def delete_contact(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """고객사 담당자 삭제 (Hard Delete)"""
    contact = await crud.customer_contact.get(db, id=id)
    if not contact:
        raise HTTPException(status_code=404, detail="해당 담당자를 찾을 수 없습니다.")

    deleted = await crud.customer_contact.remove(db, id=id)
    return ResponseEnvelope(data=deleted)
