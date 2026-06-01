"""
app/api/v1/endpoints/warranty.py — Warranty 수기 등록/조회 API
- Dell TechDirect API 연동 대신 관리자가 직접 시작일/종료일을 입력하여 저장합니다.
- GET  /warranty/server/{inventory_id}  — 서버별 워런티 조회
- PUT  /warranty/server/{inventory_id}  — 서버별 워런티 수기 등록/수정
- DELETE /warranty/server/{inventory_id} — 워런티 삭제
"""

from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.core.deps import get_db, get_current_user
from app.schemas.common import ResponseEnvelope

router = APIRouter()


# ─── Request Schema ───────────────────────────────────────────────────────────

class WarrantyUpsertRequest(BaseModel):
    start_date: date
    end_date: date
    source: str = "MANUAL"


# ─── Response helper ──────────────────────────────────────────────────────────

def _warranty_to_dict(w: models.Warranty, inventory_id: int, serial_tag: str) -> dict:
    return {
        "inventory_id": inventory_id,
        "serial_tag": serial_tag,
        "start_date": w.start_date.isoformat(),
        "end_date": w.end_date.isoformat(),
        "source": w.source,
        "last_synced": w.last_synced.isoformat() if w.last_synced else None,
    }


# ─── 기존 S/N 기반 조회 (하위 호환 유지) ────────────────────────────────────

@router.get("/{serial_no}")
async def get_warranty_by_serial(
    serial_no: str,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """S/N으로 DB에 저장된 워런티 정보를 조회합니다."""
    server_q = await db.execute(
        select(models.ServerInventory).where(
            models.ServerInventory.serial_tag == serial_no,
            models.ServerInventory.is_deleted == False,
        )
    )
    server = server_q.scalars().first()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 시리얼 넘버의 서버를 찾을 수 없습니다.",
        )

    w_q = await db.execute(
        select(models.Warranty).where(models.Warranty.server_id == server.id)
    )
    warranty = w_q.scalars().first()

    if not warranty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="등록된 워런티 정보가 없습니다.",
        )

    return ResponseEnvelope(data=_warranty_to_dict(warranty, server.id, server.serial_tag))


# ─── 서버 ID 기반 조회 ────────────────────────────────────────────────────────

@router.get("/server/{inventory_id}")
async def get_warranty_by_inventory(
    inventory_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """서버 ID로 워런티 정보를 조회합니다."""
    server = await db.get(models.ServerInventory, inventory_id)
    if not server or server.is_deleted:
        raise HTTPException(status_code=404, detail="서버를 찾을 수 없습니다.")

    w_q = await db.execute(
        select(models.Warranty).where(models.Warranty.server_id == inventory_id)
    )
    warranty = w_q.scalars().first()

    if not warranty:
        raise HTTPException(status_code=404, detail="등록된 워런티 정보가 없습니다.")

    return ResponseEnvelope(data=_warranty_to_dict(warranty, inventory_id, server.serial_tag))


# ─── 수기 등록 / 수정 (Upsert) ───────────────────────────────────────────────

@router.put("/server/{inventory_id}")
async def upsert_warranty(
    inventory_id: int,
    body: WarrantyUpsertRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    서버의 워런티 정보를 수기로 등록하거나 수정합니다.
    - 기존 레코드가 없으면 CREATE, 있으면 UPDATE (Upsert)
    - start_date / end_date / source 를 직접 입력합니다.
    """
    if body.end_date < body.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="종료일이 시작일보다 빠를 수 없습니다.",
        )

    server = await db.get(models.ServerInventory, inventory_id)
    if not server or server.is_deleted:
        raise HTTPException(status_code=404, detail="대상 서버 자산을 찾을 수 없습니다.")

    w_q = await db.execute(
        select(models.Warranty).where(models.Warranty.server_id == inventory_id)
    )
    warranty = w_q.scalars().first()

    if not warranty:
        warranty = models.Warranty(
            server_id=inventory_id,
            start_date=body.start_date,
            end_date=body.end_date,
            source=body.source,
            last_synced=datetime.now(),
        )
        db.add(warranty)
    else:
        warranty.start_date = body.start_date
        warranty.end_date = body.end_date
        warranty.source = body.source
        warranty.last_synced = datetime.now()
        db.add(warranty)

    await db.commit()
    return ResponseEnvelope(data=_warranty_to_dict(warranty, inventory_id, server.serial_tag))


# ─── 워런티 삭제 ──────────────────────────────────────────────────────────────

@router.delete("/server/{inventory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_warranty(
    inventory_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """서버의 워런티 정보를 삭제합니다."""
    w_q = await db.execute(
        select(models.Warranty).where(models.Warranty.server_id == inventory_id)
    )
    warranty = w_q.scalars().first()
    if not warranty:
        raise HTTPException(status_code=404, detail="삭제할 워런티 정보가 없습니다.")

    await db.delete(warranty)
    await db.commit()
