"""
app/services/warranty_lookup.py — 워런티 조회 대기열 공통 로직 (API 엔드포인트 + warranty-worker 공용)

흐름
  1) create_lookups  : 시리얼마다 WarrantyLookup 행 생성 (제조사 판별, AMS 서버와 연결)
       DELL + TechDirect 키 있음 → 즉시 조회 → DONE / NOT_FOUND / ERROR
       DELL + 키 없음            → WAITING_EXTENSION (브라우저 확장 프로그램이 결과를 올려 줌)
       HPE                      → PENDING (warranty-worker 가 HPE 포털에서 조회)
  2) save_result     : 조회 결과 저장 + apply_to_inventory 면 서버 워런티(warranties)에 반영
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.services.audit import log_action
from app.services.dell_warranty import dell_service
from app.services.warranty_parse import detect_vendor, normalize_serial, to_iso

logger = logging.getLogger(__name__)

SOURCE_BY_VENDOR = {"DELL": "DELL_API", "HPE": "HPE_WEB"}
OPEN_STATUSES = ("PENDING", "RUNNING", "WAITING_EXTENSION")


def lookup_to_dict(r: models.WarrantyLookup) -> dict:
    return {
        "id": r.id,
        "batch_id": r.batch_id,
        "serial_tag": r.serial_tag,
        "vendor": r.vendor,
        "status": r.status,
        "inventory_id": r.inventory_id,
        "apply_to_inventory": r.apply_to_inventory,
        "applied": r.applied,
        "start_date": to_iso(r.start_date),
        "end_date": to_iso(r.end_date),
        "service_level": r.service_level,
        "product_name": r.product_name,
        "source": r.source,
        "detail": r.detail,
        "error": r.error,
        "created_at": to_iso(r.created_at),
        "updated_at": to_iso(r.updated_at),
    }


async def _inventory_by_serial(db: AsyncSession, serials: list[str]) -> dict[str, models.ServerInventory]:
    if not serials:
        return {}
    q = await db.execute(
        select(models.ServerInventory).where(
            func.upper(models.ServerInventory.serial_tag).in_(serials),
            models.ServerInventory.is_deleted == False,  # noqa: E712
        )
    )
    return {s.serial_tag.upper(): s for s in q.scalars().all()}


async def create_lookups(
    db: AsyncSession,
    serials: list[str],
    *,
    vendor: str = "AUTO",
    apply_to_inventory: bool = False,
    user_id: int | None = None,
) -> list[models.WarrantyLookup]:
    """시리얼 목록으로 조회 요청을 만들고, Dell API 키가 있으면 Dell 건은 바로 조회까지 끝낸다."""
    uniq: list[str] = []
    for s in serials:
        n = normalize_serial(s)
        if n and n not in uniq:
            uniq.append(n)
    inv = await _inventory_by_serial(db, uniq)
    batch_id = str(uuid.uuid4())

    rows: list[models.WarrantyLookup] = []
    for s in uniq:
        server = inv.get(s)
        v = vendor if vendor in ("DELL", "HPE") else detect_vendor(s, server.vendor if server else None)
        if v == "DELL":
            status = "PENDING" if dell_service.configured else "WAITING_EXTENSION"
        elif v == "HPE":
            status = "PENDING"
        else:
            status = "ERROR"
        row = models.WarrantyLookup(
            batch_id=batch_id, serial_tag=s, vendor=v, status=status,
            inventory_id=server.id if server else None,
            apply_to_inventory=apply_to_inventory and server is not None,
            applied=False, attempts=0, requested_by_id=user_id,
            error="제조사를 판별할 수 없습니다. 제조사를 직접 선택해 다시 요청하세요." if v == "UNKNOWN" else None,
        )
        db.add(row)
        rows.append(row)
    await db.flush()

    # Dell + TechDirect 키 → 백엔드에서 즉시 조회
    dell_rows = [r for r in rows if r.vendor == "DELL" and r.status == "PENDING"]
    if dell_rows:
        results = await dell_service.fetch_many([r.serial_tag for r in dell_rows])
        for r in dell_rows:
            await save_result(db, r, results.get(r.serial_tag, {"status": "ERROR", "error": "조회 결과 없음"}),
                              source="DELL_API", user_id=user_id)
    return rows


async def save_result(
    db: AsyncSession,
    row: models.WarrantyLookup,
    result: dict,
    *,
    source: str,
    user_id: int | None = None,
) -> models.WarrantyLookup:
    """조회 결과를 대기열 행에 저장하고, 요청된 경우 AMS 서버 워런티에 반영한다."""
    row.status = result.get("status", "ERROR")
    row.start_date = result.get("start_date")
    row.end_date = result.get("end_date")
    row.service_level = (result.get("service_level") or None) and result["service_level"][:200]
    row.product_name = (result.get("product_name") or None) and result["product_name"][:200]
    row.detail = result.get("detail")
    row.error = (result.get("error") or None) and str(result["error"])[:500]
    row.source = source
    if row.status == "DONE" and row.apply_to_inventory and row.inventory_id:
        await apply_to_inventory(db, row, user_id=user_id or row.requested_by_id)
    db.add(row)
    return row


async def apply_to_inventory(db: AsyncSession, row: models.WarrantyLookup, *, user_id: int | None) -> bool:
    """조회 결과를 서버 워런티(warranties)에 Upsert 한다. 시작/종료일이 모두 있어야 반영한다."""
    if not (row.inventory_id and row.start_date and row.end_date):
        row.error = row.error or "시작일 또는 종료일이 없어 서버 워런티에 반영하지 못했습니다."
        return False
    q = await db.execute(select(models.Warranty).where(models.Warranty.server_id == row.inventory_id))
    w = q.scalars().first()
    before = None
    if w:
        before = {"start_date": to_iso(w.start_date), "end_date": to_iso(w.end_date), "source": w.source}
        w.start_date, w.end_date = row.start_date, row.end_date
    else:
        w = models.Warranty(server_id=row.inventory_id, start_date=row.start_date, end_date=row.end_date)
    w.source = row.source or SOURCE_BY_VENDOR.get(row.vendor, "MANUAL")
    w.service_level = row.service_level
    w.detail = row.detail
    w.last_synced = datetime.now(timezone.utc)
    db.add(w)
    await log_action(
        db, user_id=user_id, action="UPDATE" if before else "CREATE", resource_type="WARRANTY",
        resource_id=row.inventory_id, before=before,
        after={"start_date": to_iso(row.start_date), "end_date": to_iso(row.end_date), "source": w.source,
               "service_level": row.service_level, "lookup_id": row.id},
    )
    row.applied = True
    return True


async def heartbeat(db: AsyncSession, name: str, state: str, message: str | None = None) -> None:
    """작업자 상태 기록 (warranty-worker 가 주기적으로 호출)"""
    q = await db.execute(select(models.WarrantyWorkerStatus).where(models.WarrantyWorkerStatus.name == name))
    st = q.scalars().first()
    now = datetime.now(timezone.utc)
    if not st:
        st = models.WarrantyWorkerStatus(name=name, state=state, message=message, last_seen=now)
    else:
        st.state, st.message, st.last_seen = state, message, now
    db.add(st)


def warranty_state(end: date | None, base: date | None = None) -> str | None:
    """기준일(기본: 오늘) 기준 워런티 In/Out"""
    if not end:
        return None
    return "IN" if end >= (base or date.today()) else "OUT"
