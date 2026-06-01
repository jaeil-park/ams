from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_admin
from app.crud import crud_user
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserOut
from app.schemas.common import ResponseEnvelope

router = APIRouter()

@router.get("", response_model=ResponseEnvelope)
async def read_users(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_admin),
) -> Any:
    """사용자 목록을 조회합니다 (ADMIN 전용)."""
    from sqlalchemy import select, func
    
    query = select(User).offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()
    
    count_query = select(func.count(User.id))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    users_out = [UserOut.model_validate(u) for u in users]
    
    total_pages = (total + limit - 1) // limit if limit > 0 else 1
    page = (skip // limit) + 1 if limit > 0 else 1
    
    return ResponseEnvelope(
        data=users_out,
        meta={"total": total, "page": page, "limit": limit, "total_pages": total_pages}
    )

@router.post("", response_model=ResponseEnvelope)
async def create_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: UserCreate,
    current_user: User = Depends(require_admin),
) -> Any:
    """새 사용자를 생성합니다 (ADMIN 전용)."""
    user = await crud_user.user.create(db=db, obj_in=user_in)
    return ResponseEnvelope(data=UserOut.model_validate(user))

@router.get("/{id}", response_model=ResponseEnvelope)
async def read_user(
    *,
    db: AsyncSession = Depends(get_db),
    id: int,
    current_user: User = Depends(require_admin),
) -> Any:
    """특정 사용자를 조회합니다 (ADMIN 전용)."""
    user = await crud_user.user.get(db=db, id=id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    return ResponseEnvelope(data=UserOut.model_validate(user))

@router.patch("/{id}", response_model=ResponseEnvelope)
async def update_user(
    *,
    db: AsyncSession = Depends(get_db),
    id: int,
    user_in: UserUpdate,
    current_user: User = Depends(require_admin),
) -> Any:
    """사용자 정보를 수정합니다 (ADMIN 전용)."""
    user = await crud_user.user.get(db=db, id=id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    user = await crud_user.user.update(db=db, db_obj=user, obj_in=user_in)
    return ResponseEnvelope(data=UserOut.model_validate(user))

@router.delete("/{id}", response_model=ResponseEnvelope)
async def delete_user(
    *,
    db: AsyncSession = Depends(get_db),
    id: int,
    current_user: User = Depends(require_admin),
) -> Any:
    """사용자를 비활성화 처리합니다 (논리 삭제) (ADMIN 전용)."""
    user = await crud_user.user.get(db=db, id=id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    # 자기 자신은 비활성화 할 수 없음
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="자기 자신의 계정은 비활성화할 수 없습니다.")
        
    user_in = UserUpdate(is_active=False)
    user = await crud_user.user.update(db=db, db_obj=user, obj_in=user_in)
    return ResponseEnvelope(data=UserOut.model_validate(user))
