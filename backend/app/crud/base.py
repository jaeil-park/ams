"""
app/crud/base.py — Generic 비동기 CRUDBase 정의
- SQLAlchemy 2.0 async 문법을 철저히 준수합니다.
- Soft Delete 모델(`is_deleted`)에 대응하는 로직을 기본 포함합니다.
"""

from collections.abc import Sequence
from typing import Any, Generic, Type, TypeVar
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        """
        CRUD base class with default methods to Create, Read, Update, Delete (CRUD).
        """
        self.model = model

    async def get(self, db: AsyncSession, id: Any) -> ModelType | None:
        """단건 조회"""
        query = select(self.model).where(self.model.id == id)
        
        # Soft delete 모델인 경우 필터링 추가
        if hasattr(self.model, "is_deleted"):
            query = query.where(self.model.is_deleted == False)
            
        result = await db.execute(query)
        return result.scalars().first()

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> Sequence[ModelType]:
        """다건 목록 조회 (페이지네이션 기본 적용)"""
        query = select(self.model)
        
        if hasattr(self.model, "is_deleted"):
            query = query.where(self.model.is_deleted == False)
            
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        """데이터 생성"""
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any]
    ) -> ModelType:
        """데이터 부분 수정(PATCH)"""
        obj_data = db_obj.__dict__
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
            
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
                
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def remove(self, db: AsyncSession, *, id: int) -> ModelType | None:
        """데이터 삭제 (Soft Delete 지원 시 is_deleted=True 처리, 그 외 하드 삭제)"""
        db_obj = await self.get(db, id)
        if not db_obj:
            return None
            
        if hasattr(db_obj, "is_deleted"):
            db_obj.is_deleted = True
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)
        else:
            await db.delete(db_obj)
            await db.commit()
            
        return db_obj
