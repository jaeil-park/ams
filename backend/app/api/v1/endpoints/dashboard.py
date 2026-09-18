"""
app/api/v1/endpoints/dashboard.py — 대시보드 통계 및 KPI API
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.core.deps import get_db, get_current_user
from app.schemas.common import ResponseEnvelope

router = APIRouter()


@router.get("/kpi")
async def get_dashboard_kpi(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    [대시보드 KPI 조회]
    - 입고 대기(재고) 서버 수
    - 납품 예정 프로젝트 수
    - 현재 진행중인 프로젝트 수
    - 납품 완료 프로젝트 수
    """
    # 1. 재고 상태인 서버 개수
    stock_srv_query = select(func.count(models.ServerInventory.id)).where(
        models.ServerInventory.status == "IN_STOCK",
        models.ServerInventory.is_deleted == False
    )
    stock_srv_res = await db.execute(stock_srv_query)
    stock_srv_count = stock_srv_res.scalar() or 0
    
    # 2. WAITING 상태 프로젝트 수
    waiting_proj_query = select(func.count(models.Project.id)).where(
        models.Project.status == "WAITING",
        models.Project.is_deleted == False
    )
    waiting_proj_res = await db.execute(waiting_proj_query)
    waiting_proj_count = waiting_proj_res.scalar() or 0
    
    # 3. IN_PROGRESS 상태 프로젝트 수
    progress_proj_query = select(func.count(models.Project.id)).where(
        models.Project.status == "IN_PROGRESS",
        models.Project.is_deleted == False
    )
    progress_proj_res = await db.execute(progress_proj_query)
    progress_proj_count = progress_proj_res.scalar() or 0
    
    # 4. COMPLETED 상태 프로젝트 수
    completed_proj_query = select(func.count(models.Project.id)).where(
        models.Project.status == "COMPLETED",
        models.Project.is_deleted == False
    )
    completed_proj_res = await db.execute(completed_proj_query)
    completed_proj_count = completed_proj_res.scalar() or 0
    
    return ResponseEnvelope(data={
        "in_stock_servers": stock_srv_count,
        "waiting_projects": waiting_proj_count,
        "in_progress_projects": progress_proj_count,
        "completed_projects": completed_proj_count
    })


@router.get("/customer-delivery")
async def get_customer_delivery_summary(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """[대시보드 차트] 고객사별 납품 장비 대수 현황 통계"""
    # 고객사별, 서버의 status별 개수 group by
    query = (
        select(
            models.Customer.name.label("customer_name"),
            models.ServerInventory.status.label("status"),
            func.count(models.ServerInventory.id).label("count")
        )
        .join(models.Project, models.Project.id == models.ServerInventory.project_id)
        .join(models.Customer, models.Customer.id == models.Project.customer_id)
        .where(
            models.ServerInventory.is_deleted == False,
            models.Project.is_deleted == False,
            models.Customer.is_deleted == False
        )
        .group_by(models.Customer.name, models.ServerInventory.status)
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    # 프론트엔드가 차트 그리기 편하도록 포맷 가공
    summary = {}
    for r in rows:
        c_name = r.customer_name
        status_label = r.status
        count_val = r.count
        
        if c_name not in summary:
            summary[c_name] = {}
        summary[c_name][status_label] = count_val
        
    formatted_data = []
    for customer, statuses in summary.items():
        formatted_data.append({
            "customer": customer,
            "statuses": statuses
        })
        
    return ResponseEnvelope(data=formatted_data)


@router.get("/parts-summary")
async def get_parts_summary(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    [대시보드 차트] 파트 구분(카테고리)별 재고 수량 도넛 차트 통계
    - 모델 단위로 쪼개면 항목이 수십 개로 늘어나 도넛이 읽히지 않으므로 카테고리로 묶는다.
    - 카테고리가 비어 있는 레코드는 '미분류'로 집계한다.
    """
    query = (
        select(
            models.PartInventory.category.label("category"),
            func.sum(models.PartInventory.qty).label("total_qty"),
            func.count(models.PartInventory.id).label("item_count"),
        )
        .where(models.PartInventory.is_deleted == False)
        .group_by(models.PartInventory.category)
    )

    result = await db.execute(query)
    rows = result.all()

    formatted_data = [
        {
            "category": r.category or "미분류",
            "qty": int(r.total_qty or 0),
            "item_count": int(r.item_count or 0),
        }
        for r in rows
    ]
    formatted_data.sort(key=lambda x: x["qty"], reverse=True)
    return ResponseEnvelope(data=formatted_data)
