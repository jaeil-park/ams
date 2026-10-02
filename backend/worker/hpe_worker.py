"""
worker/hpe_worker.py — HPE 워런티 자동 조회 작업자 (warranty-worker 컨테이너)

실행: python -m worker.hpe_worker

- warranty_lookups 에서 vendor=HPE, status=PENDING 건을 가져와 HPE 포털에서 조회한다.
- 조회 결과는 대기열 행에 저장하고, 요청 시 서버 워런티(warranties)에 반영한다.
- 상태는 warranty_worker_statuses(name='HPE')에 주기적으로 기록한다 → AMS '워런티 조회' 화면에 표시
- 로그인 불가(캡차·MFA·계정 오류) 시 대기 건은 그대로 두고 HPE_LOGIN_RETRY_SEC 뒤 다시 시도한다.
"""

from __future__ import annotations

import asyncio
import logging
import signal

from sqlalchemy import select, update

from app import models
from app.core.config import settings
from app.db.session import async_session
from app.services.hpe_portal import HpeLoginRequired, HpePortalClient
from app.services.warranty_lookup import heartbeat, save_result

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
logger = logging.getLogger("hpe_worker")

NAME = "HPE"
MAX_ATTEMPTS = 3
CLAIM = 5
_stop = asyncio.Event()


async def _beat(state: str, message: str | None = None) -> None:
    async with async_session() as db:
        await heartbeat(db, NAME, state, message)
        await db.commit()


async def _reset_running() -> None:
    """이전 실행 중 멈춘 RUNNING 건을 대기로 되돌린다."""
    async with async_session() as db:
        await db.execute(
            update(models.WarrantyLookup)
            .where(models.WarrantyLookup.vendor == NAME, models.WarrantyLookup.status == "RUNNING")
            .values(status="PENDING")
        )
        await db.commit()


async def _claim() -> list[int]:
    async with async_session() as db:
        rows = (await db.execute(
            select(models.WarrantyLookup)
            .where(models.WarrantyLookup.vendor == NAME, models.WarrantyLookup.status == "PENDING",
                   models.WarrantyLookup.is_deleted == False)  # noqa: E712 — 삭제(취소)된 건 제외
            .order_by(models.WarrantyLookup.id)
            .limit(CLAIM)
            .with_for_update(skip_locked=True)
        )).scalars().all()
        for r in rows:
            r.status = "RUNNING"
            r.attempts = (r.attempts or 0) + 1
        await db.commit()
        return [r.id for r in rows]


async def _set_status(lookup_id: int, status: str, error: str | None = None) -> None:
    async with async_session() as db:
        r = await db.get(models.WarrantyLookup, lookup_id)
        if r:
            r.status, r.error = status, error
            await db.commit()


async def _process(client: HpePortalClient, lookup_id: int) -> None:
    async with async_session() as db:
        row = await db.get(models.WarrantyLookup, lookup_id)
        if row is None or row.is_deleted:
            return  # 대기 중 삭제(취소)된 건
        serial, attempts = row.serial_tag, row.attempts
    logger.info("HPE 조회: %s (시도 %d)", serial, attempts)
    try:
        result = await client.lookup(serial)
    except HpeLoginRequired:
        await _set_status(lookup_id, "PENDING")
        raise
    except Exception as e:  # noqa: BLE001 — 브라우저/네트워크 오류는 재시도
        logger.exception("HPE 조회 오류: %s", serial)
        if attempts >= MAX_ATTEMPTS:
            await _set_status(lookup_id, "ERROR", f"HPE 조회 오류 ({attempts}회): {e}"[:500])
        else:
            await _set_status(lookup_id, "PENDING", f"재시도 예정: {e}"[:500])
        return
    async with async_session() as db:
        row = await db.get(models.WarrantyLookup, lookup_id)
        await save_result(db, row, result, source="HPE_WEB")
        await db.commit()
    logger.info("HPE 조회 완료: %s → %s %s", serial, result.get("status"), result.get("end_date"))


async def run() -> None:
    await _reset_running()
    client: HpePortalClient | None = None
    while not _stop.is_set():
        try:
            if client is None:
                client = HpePortalClient()
                await client.start()
                await client.ensure_login()
                await _beat("READY", "HPE 포털 로그인 상태 정상")

            ids = await _claim()
            if not ids:
                await _beat("READY", "대기 건 없음")
                await _sleep(settings.HPE_POLL_SEC)
                continue
            await _beat("BUSY", f"{len(ids)}건 조회 중")
            for i in ids:
                await _process(client, i)
                await _sleep(settings.HPE_LOOKUP_DELAY_SEC)

        except HpeLoginRequired as e:
            logger.warning("HPE 로그인 필요: %s", e)
            await _beat("LOGIN_REQUIRED", str(e)[:500])
            client = await _close(client)
            await _sleep(settings.HPE_LOGIN_RETRY_SEC)
        except Exception as e:  # noqa: BLE001 — 작업자는 죽지 않고 브라우저를 새로 띄운다
            logger.exception("작업자 오류")
            await _beat("ERROR", str(e)[:500])
            client = await _close(client)
            await _sleep(30)
    await _close(client)


async def _close(client: HpePortalClient | None) -> None:
    if client:
        await client.close()
    return None


async def _sleep(sec: float) -> None:
    try:
        await asyncio.wait_for(_stop.wait(), timeout=sec)
    except asyncio.TimeoutError:
        pass


def main() -> None:
    loop = asyncio.new_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _stop.set)
        except (NotImplementedError, RuntimeError):  # Windows 로컬 실행
            pass
    loop.run_until_complete(run())


if __name__ == "__main__":
    main()
