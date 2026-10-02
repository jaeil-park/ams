"""
app/api/v1/endpoints/warranty_lookups.py — 제조사 워런티 자동 조회 API

POST /warranty-lookups                 시리얼 목록 조회 요청 (제조사 자동 판별)
POST /warranty-lookups/inventory       AMS 서버(id 목록 또는 프로젝트) 기준 조회 + 서버 워런티 반영
GET  /warranty-lookups                 요청 결과 조회 (batch_id) / 최근 조회 이력
GET  /warranty-lookups/status          조회 경로 상태 (Dell API·확장 프로그램 대기, HPE 작업자 로그인 상태)
GET  /warranty-lookups/pending-dell    Dell 확장 프로그램이 처리할 대기 건
POST /warranty-lookups/{id}/result     Dell 확장 프로그램이 조회 결과 등록
POST /warranty-lookups/{id}/retry      실패/중단 건 재요청
"""

from datetime import date, datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.schemas.common import ResponseEnvelope
from app.services.audit import log_action
from app.services.dell_warranty import dell_service
from app.services.warranty_lookup import (
    OPEN_STATUSES,
    create_lookups,
    lookup_to_dict,
    save_result,
)

router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────────────────────────

class LookupCreate(BaseModel):
    serials: list[str] = Field(..., min_length=1)
    vendor: Literal["AUTO", "DELL", "HPE"] = "AUTO"
    apply_to_inventory: bool = False


class InventoryLookupCreate(BaseModel):
    inventory_ids: list[int] | None = None
    project_id: int | None = None
    apply_to_inventory: bool = True


class LookupDelete(BaseModel):
    ids: list[int] = Field(..., min_length=1, max_length=500)


class ExtensionResult(BaseModel):
    status: Literal["DONE", "NOT_FOUND", "ERROR"]
    start_date: date | None = None
    end_date: date | None = None
    service_level: str | None = Field(None, max_length=200)
    product_name: str | None = Field(None, max_length=200)
    error: str | None = Field(None, max_length=500)
    detail: dict | None = None


async def _batch_out(db: AsyncSession, rows: list[models.WarrantyLookup]) -> dict:
    # commit 후 DB가 갱신한 updated_at 등은 만료 상태라 다시 읽어 와야 응답에 쓸 수 있다
    for r in rows:
        await db.refresh(r)
    return {"batch_id": rows[0].batch_id if rows else None, "rows": [lookup_to_dict(r) for r in rows]}


async def _one_out(db: AsyncSession, row: models.WarrantyLookup) -> dict:
    await db.refresh(row)
    return lookup_to_dict(row)


# ─── 조회 요청 ─────────────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_lookup(
    body: LookupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """시리얼 목록 워런티 조회 요청. AMS에 등록된 서버면 apply_to_inventory=True 로 워런티까지 반영할 수 있다."""
    serials = [s for s in body.serials if s and s.strip()]
    if not serials:
        raise HTTPException(status_code=400, detail="조회할 시리얼을 입력하세요.")
    if len(serials) > settings.WARRANTY_LOOKUP_MAX:
        raise HTTPException(status_code=400, detail=f"한 번에 최대 {settings.WARRANTY_LOOKUP_MAX}건까지 조회할 수 있습니다.")
    rows = await create_lookups(db, serials, vendor=body.vendor,
                                apply_to_inventory=body.apply_to_inventory, user_id=current_user.id)
    await db.commit()
    return ResponseEnvelope(data=await _batch_out(db, rows))


@router.post("/inventory", status_code=status.HTTP_201_CREATED)
async def create_inventory_lookup(
    body: InventoryLookupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """AMS 서버(id 목록 또는 프로젝트 소속 서버 전체)의 워런티를 조회해 서버 워런티에 반영한다."""
    if not body.inventory_ids and not body.project_id:
        raise HTTPException(status_code=400, detail="inventory_ids 또는 project_id 가 필요합니다.")
    q = select(models.ServerInventory).where(models.ServerInventory.is_deleted == False)  # noqa: E712
    if body.inventory_ids:
        q = q.where(models.ServerInventory.id.in_(body.inventory_ids))
    if body.project_id:
        q = q.where(models.ServerInventory.project_id == body.project_id)
    servers = (await db.execute(q)).scalars().all()
    if not servers:
        raise HTTPException(status_code=404, detail="조회할 서버가 없습니다.")
    if len(servers) > settings.WARRANTY_LOOKUP_MAX:
        raise HTTPException(status_code=400, detail=f"한 번에 최대 {settings.WARRANTY_LOOKUP_MAX}대까지 조회할 수 있습니다.")
    rows = await create_lookups(db, [s.serial_tag for s in servers],
                                apply_to_inventory=body.apply_to_inventory, user_id=current_user.id)
    await db.commit()
    return ResponseEnvelope(data=await _batch_out(db, rows))


# ─── 결과 / 이력 ───────────────────────────────────────────────────────────────

@router.get("")
async def list_lookups(
    batch_id: str | None = Query(None),
    serial: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """batch_id 가 있으면 그 요청의 결과, 없으면 최근 조회 이력"""
    q = select(models.WarrantyLookup).where(models.WarrantyLookup.is_deleted == False)  # noqa: E712
    if batch_id:
        q = q.where(models.WarrantyLookup.batch_id == batch_id).order_by(models.WarrantyLookup.id)
    else:
        if serial:
            q = q.where(models.WarrantyLookup.serial_tag.ilike(f"%{serial.strip()}%"))
        q = q.order_by(models.WarrantyLookup.id.desc()).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return ResponseEnvelope(data=[lookup_to_dict(r) for r in rows])


@router.get("/status")
async def lookup_status(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """조회 경로 상태: Dell(API/확장 프로그램), HPE 작업자(로그인 상태·마지막 응답), 대기 건수"""
    counts = dict((await db.execute(
        select(models.WarrantyLookup.vendor, func.count())
        .where(models.WarrantyLookup.status.in_(OPEN_STATUSES),
               models.WarrantyLookup.is_deleted == False)  # noqa: E712
        .group_by(models.WarrantyLookup.vendor)
    )).all())
    workers = {}
    now = datetime.now(timezone.utc)
    for w in (await db.execute(select(models.WarrantyWorkerStatus))).scalars().all():
        age = (now - w.last_seen).total_seconds()
        workers[w.name] = {
            "state": "STOPPED" if age > settings.WARRANTY_WORKER_STALE_SEC else w.state,
            "message": w.message,
            "last_seen": w.last_seen.isoformat(),
        }
    return ResponseEnvelope(data={
        "dell_mode": "API" if dell_service.configured else "EXTENSION",
        "workers": workers,
        "open_counts": counts,
    })


# ─── Dell 브라우저 확장 프로그램 연동 ──────────────────────────────────────────

@router.get("/pending-dell")
async def pending_dell(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """확장 프로그램이 Dell 사이트에서 조회할 대기 건 (오래된 순)"""
    rows = (await db.execute(
        select(models.WarrantyLookup)
        .where(models.WarrantyLookup.vendor == "DELL", models.WarrantyLookup.status == "WAITING_EXTENSION",
               models.WarrantyLookup.is_deleted == False)  # noqa: E712
        .order_by(models.WarrantyLookup.id).limit(limit)
    )).scalars().all()
    return ResponseEnvelope(data=[{"id": r.id, "serial_tag": r.serial_tag} for r in rows])


@router.post("/{lookup_id}/result")
async def post_extension_result(
    lookup_id: int,
    body: ExtensionResult,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Dell 확장 프로그램이 조회한 결과를 등록한다. (Dell 대기 건만 허용)"""
    row = await db.get(models.WarrantyLookup, lookup_id)
    if not row or row.is_deleted:
        raise HTTPException(status_code=404, detail="조회 요청을 찾을 수 없습니다.")
    if row.vendor != "DELL" or row.status not in ("WAITING_EXTENSION", "RUNNING"):
        raise HTTPException(status_code=409, detail="확장 프로그램 결과를 받을 수 있는 상태가 아닙니다.")
    if body.status == "DONE" and (not body.end_date or (body.start_date and body.end_date < body.start_date)):
        raise HTTPException(status_code=400, detail="종료일이 없거나 시작일보다 빠릅니다.")
    await save_result(db, row, body.model_dump(), source="DELL_WEB", user_id=current_user.id)
    await db.commit()
    return ResponseEnvelope(data=await _one_out(db, row))


@router.post("/{lookup_id}/retry")
async def retry_lookup(
    lookup_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """실패(ERROR)·미발견(NOT_FOUND) 건을 다시 대기열에 넣는다."""
    row = await db.get(models.WarrantyLookup, lookup_id)
    if not row or row.is_deleted:
        raise HTTPException(status_code=404, detail="조회 요청을 찾을 수 없습니다.")
    if row.vendor not in ("DELL", "HPE"):
        raise HTTPException(status_code=400, detail="제조사를 알 수 없는 건은 제조사를 지정해 새로 요청하세요.")
    if row.vendor == "DELL" and dell_service.configured:
        rows = await create_lookups(db, [row.serial_tag], vendor="DELL",
                                    apply_to_inventory=row.apply_to_inventory, user_id=current_user.id)
        await db.commit()
        return ResponseEnvelope(data=await _one_out(db, rows[0]))
    row.status = "WAITING_EXTENSION" if row.vendor == "DELL" else "PENDING"
    row.error = None
    db.add(row)
    await db.commit()
    return ResponseEnvelope(data=await _one_out(db, row))


# ─── 조회 기록 삭제 (숨김) ─────────────────────────────────────────────────────

@router.post("/delete")
async def delete_lookups(
    body: LookupDelete,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    조회 기록을 삭제(숨김)한다. 대기·진행 중인 건은 조회도 취소된다.
    이미 서버 워런티(warranties)에 반영된 값은 그대로 둔다.
    """
    rows = (await db.execute(
        select(models.WarrantyLookup).where(
            models.WarrantyLookup.id.in_(body.ids),
            models.WarrantyLookup.is_deleted == False,  # noqa: E712
        )
    )).scalars().all()
    for r in rows:
        r.is_deleted = True
        db.add(r)
    await log_action(
        db, user_id=current_user.id, action="DELETE", resource_type="WARRANTY_LOOKUP",
        after={"ids": [r.id for r in rows], "serials": [r.serial_tag for r in rows]},
    )
    await db.commit()
    return ResponseEnvelope(data={"deleted": len(rows)})

