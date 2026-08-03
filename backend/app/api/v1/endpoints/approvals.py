"""
app/api/v1/endpoints/approvals.py — Admin 전용 결재/승인 관리 API
"""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, models, schemas
from app.core.deps import get_db, require_admin
from app.schemas.common import ResponseEnvelope, MetaSchema

router = APIRouter()


@router.get("", response_model=ResponseEnvelope[list[schemas.part.ApprovalOut]])
async def list_approvals(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """결재 대기 목록 조회 (ADMIN 전용)"""
    skip = (page - 1) * limit
    
    query = select(models.Approval)
    count_query = select(func.count(models.Approval.id))
    
    if status_filter:
        query = query.where(models.Approval.status == status_filter)
        count_query = count_query.where(models.Approval.status == status_filter)
        
    query = query.order_by(models.Approval.created_at.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    approvals = result.scalars().all()
    
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    total_pages = (total + limit - 1) // limit
    
    return ResponseEnvelope(
        data=approvals,
        meta=MetaSchema(
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )
    )


@router.post("/{id}/approve", response_model=ResponseEnvelope[schemas.part.ApprovalOut])
async def approve_request(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """결재 요청 최종 승인 및 비즈니스 객체 반영 (ADMIN 전용)"""
    approval = await db.get(models.Approval, id)
    if not approval:
        raise HTTPException(status_code=404, detail="해당 결재 요청을 찾을 수 없습니다.")
        
    if approval.status != "PENDING":
        raise HTTPException(status_code=400, detail="이미 처리 완료된 결재 요청입니다.")
        
    # resource_type별 실적 반영 분기
    if approval.resource_type == "PART_QTY":
        part = await crud.part_inventory.get(db, id=approval.resource_id)
        if not part:
            raise HTTPException(status_code=404, detail="수정 대상 부품이 존재하지 않습니다.")
            
        new_qty = approval.payload.get("qty")
        if new_qty is None or new_qty < 0:
            raise HTTPException(status_code=400, detail="승인 페이로드에 올바르지 않은 수량이 적혀있습니다.")
            
        # 감사 로그를 기록하기 위한 이전 값 저장
        before_state = {"qty": part.qty}
        
        # 실제 수량 강제 조율
        part.qty = new_qty
        db.add(part)
        
        # 감사 로그(Audit Log) 등록
        audit = models.AuditLog(
            user_id=current_user.id,
            action="UPDATE",
            resource_type="PART",
            resource_id=part.id,
            before=before_state,
            after={"qty": new_qty}
        )
        db.add(audit)

    elif approval.resource_type == "PART_USAGE":
        part = await crud.part_inventory.get(db, id=approval.resource_id)
        if not part:
            raise HTTPException(status_code=404, detail="출고 대상 부품이 존재하지 않습니다.")

        payload = approval.payload
        usage_qty = payload.get("qty")
        if usage_qty is None or usage_qty <= 0:
            raise HTTPException(status_code=400, detail="승인 페이로드에 올바르지 않은 수량이 적혀있습니다.")

        # 요청 시점 이후 재고가 줄었을 수 있으므로 승인 시점에 다시 검증
        if part.qty < usage_qty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"승인 시점 재고가 부족합니다. (현재 재고: {part.qty}, 요청 수량: {usage_qty})"
            )

        before_state = {"qty": part.qty}
        part.qty -= usage_qty
        db.add(part)

        new_usage = models.PartUsage(
            part_id=part.id,
            used_date=date.fromisoformat(payload["used_date"]) if payload.get("used_date") else date.today(),
            customer_id=payload.get("customer_id"),
            location=payload.get("location"),
            reason=payload.get("reason"),
            qty=usage_qty,
            po_number=payload.get("po_number"),
        )
        db.add(new_usage)

        audit = models.AuditLog(
            user_id=current_user.id,
            action="UPDATE",
            resource_type="PART",
            resource_id=part.id,
            before=before_state,
            after={"qty": part.qty, "usage_qty": usage_qty},
        )
        db.add(audit)

    # 상태 갱신
    approval.status = "APPROVED"
    approval.approver_id = current_user.id
    db.add(approval)
    await db.commit()
    await db.refresh(approval)
    
    return ResponseEnvelope(data=approval)


@router.post("/{id}/reject", response_model=ResponseEnvelope[schemas.part.ApprovalOut])
async def reject_request(
    id: int,
    reason: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """결재 요청 반려 (ADMIN 전용)"""
    approval = await db.get(models.Approval, id)
    if not approval:
        raise HTTPException(status_code=404, detail="해당 결재 요청을 찾을 수 없습니다.")
        
    if approval.status != "PENDING":
        raise HTTPException(status_code=400, detail="이미 처리 완료된 결재 요청입니다.")
        
    approval.status = "REJECTED"
    approval.approver_id = current_user.id
    if reason:
        approval.reason = reason
        
    db.add(approval)
    await db.commit()
    await db.refresh(approval)
    
    return ResponseEnvelope(data=approval)
