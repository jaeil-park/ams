"""
app/api/v1/endpoints/system_logs.py — 시스템 오류/실패 로그 조회 API (ADMIN 전용)
"""

from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.core.deps import get_db, require_admin
from app.schemas.common import ResponseEnvelope, MetaSchema

router = APIRouter()


@router.get("", response_model=ResponseEnvelope[list[schemas.SystemLogOut]])
async def list_system_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    level: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """시스템 오류/실패 로그 목록 조회 (ADMIN 전용)"""
    skip = (page - 1) * limit

    query = select(models.SystemLog)
    count_query = select(func.count(models.SystemLog.id))

    if level:
        query = query.where(models.SystemLog.level == level)
        count_query = count_query.where(models.SystemLog.level == level)

    if date_from:
        query = query.where(models.SystemLog.created_at >= date_from)
        count_query = count_query.where(models.SystemLog.created_at >= date_from)

    if date_to:
        end_dt = datetime.combine(date_to, datetime.max.time())
        query = query.where(models.SystemLog.created_at <= end_dt)
        count_query = count_query.where(models.SystemLog.created_at <= end_dt)

    query = query.order_by(models.SystemLog.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    total_pages = (total + limit - 1) // limit

    return ResponseEnvelope(
        data=logs,
        meta=MetaSchema(total=total, page=page, limit=limit, total_pages=total_pages),
    )
