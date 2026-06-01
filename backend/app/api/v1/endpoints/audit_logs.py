"""
app/api/v1/endpoints/audit_logs.py — 감사 로그 조회 API (ADMIN 전용)
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from app import models, schemas
from app.core.deps import get_db, require_admin
from app.schemas.common import ResponseEnvelope, MetaSchema

router = APIRouter()


@router.get("", response_model=ResponseEnvelope[list[schemas.AuditLogOut]])
async def list_audit_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    user_id: int | None = Query(None),
    resource_type: str | None = Query(None),
    action: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """감사 로그 목록 조회 (ADMIN 전용)"""
    skip = (page - 1) * limit

    query = select(models.AuditLog)
    count_query = select(func.count(models.AuditLog.id))

    if user_id is not None:
        query = query.where(models.AuditLog.user_id == user_id)
        count_query = count_query.where(models.AuditLog.user_id == user_id)

    if resource_type:
        query = query.where(models.AuditLog.resource_type == resource_type)
        count_query = count_query.where(models.AuditLog.resource_type == resource_type)

    if action:
        query = query.where(models.AuditLog.action == action)
        count_query = count_query.where(models.AuditLog.action == action)

    if date_from:
        query = query.where(models.AuditLog.created_at >= date_from)
        count_query = count_query.where(models.AuditLog.created_at >= date_from)

    if date_to:
        from datetime import datetime, timedelta
        end_dt = datetime.combine(date_to, datetime.max.time())
        query = query.where(models.AuditLog.created_at <= end_dt)
        count_query = count_query.where(models.AuditLog.created_at <= end_dt)

    query = query.order_by(models.AuditLog.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    total_pages = (total + limit - 1) // limit

    return ResponseEnvelope(
        data=logs,
        meta=MetaSchema(total=total, page=page, limit=limit, total_pages=total_pages),
    )
