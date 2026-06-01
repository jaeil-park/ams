"""
app/api/v1/endpoints/search.py — 전역 통합 검색 API
GET /api/v1/search?q= — S/N, 고객사명, 모델명, 프로젝트명 동시 검색
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.core.deps import get_db, get_current_user
from app.schemas.common import ResponseEnvelope

router = APIRouter()


@router.get("")
async def global_search(
    q: str = Query(..., min_length=1, description="검색어 (S/N, 고객사명, 모델명, 프로젝트명)"),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    S/N, 고객사명, 모델명, 프로젝트명 통합 검색.
    카테고리별 최대 5건 반환.
    """
    if not q or len(q.strip()) < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="검색어를 입력해주세요.")

    pattern = f"%{q.strip()}%"

    # 서버 인벤토리 (serial_tag, model, host_name)
    server_q = await db.execute(
        select(models.ServerInventory)
        .where(
            models.ServerInventory.is_deleted == False,
            (
                models.ServerInventory.serial_tag.ilike(pattern)
                | models.ServerInventory.model.ilike(pattern)
                | models.ServerInventory.host_name.ilike(pattern)
            ),
        )
        .limit(5)
    )
    servers = server_q.scalars().all()

    # 파트 인벤토리 (model, category)
    part_q = await db.execute(
        select(models.PartInventory)
        .where(
            models.PartInventory.is_deleted == False,
            (
                models.PartInventory.model.ilike(pattern)
                | models.PartInventory.category.ilike(pattern)
            ),
        )
        .limit(5)
    )
    parts = part_q.scalars().all()

    # 고객사 (name, code)
    customer_q = await db.execute(
        select(models.Customer)
        .where(
            models.Customer.is_deleted == False,
            (
                models.Customer.name.ilike(pattern)
                | models.Customer.code.ilike(pattern)
            ),
        )
        .limit(5)
    )
    customers = customer_q.scalars().all()

    # 프로젝트 (name, po_number)
    project_q = await db.execute(
        select(models.Project)
        .where(
            models.Project.is_deleted == False,
            (
                models.Project.name.ilike(pattern)
                | models.Project.po_number.ilike(pattern)
            ),
        )
        .limit(5)
    )
    projects = project_q.scalars().all()

    return ResponseEnvelope(
        data={
            "query": q.strip(),
            "servers": [
                {
                    "id": s.id,
                    "serial_tag": s.serial_tag,
                    "model": s.model,
                    "status": s.status,
                    "category": s.category,
                }
                for s in servers
            ],
            "parts": [
                {
                    "id": p.id,
                    "model": p.model,
                    "category": p.category,
                    "qty": p.qty,
                    "status": p.status,
                }
                for p in parts
            ],
            "customers": [
                {
                    "id": c.id,
                    "code": c.code,
                    "name": c.name,
                    "status": c.status,
                }
                for c in customers
            ],
            "projects": [
                {
                    "id": p.id,
                    "name": p.name,
                    "po_number": p.po_number,
                    "status": p.status,
                }
                for p in projects
            ],
        }
    )
