"""
app/api/v1/endpoints/integrations.py — 사내 다른 시스템용 읽기 전용 연동 API

GET /integrations/warranties   제조사 워런티 조회 결과 (시리얼당 1건) — 이력 검색 서버 '장비 대장' 연동용

사용자 로그인(JWT) 대신 연동 전용 토큰(X-Integration-Token)을 쓴다. 값은 서버 환경변수 INTEGRATION_TOKEN 으로만
넣고, 비어 있거나 너무 짧으면 API 자체를 닫는다(403). 고객사·프로젝트·사용자 정보는 내보내지 않는다.
"""

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.core.config import settings
from app.core.deps import get_db
from app.schemas.common import ResponseEnvelope

router = APIRouter()

MIN_TOKEN_LEN = 32


def require_integration_token(x_integration_token: str | None = Header(None)) -> None:
    """연동 전용 토큰 검증"""
    expected = settings.INTEGRATION_TOKEN.strip()
    if len(expected) < MIN_TOKEN_LEN:
        raise HTTPException(status_code=403, detail="연동 API 가 꺼져 있습니다.")
    if not secrets.compare_digest((x_integration_token or "").encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="연동 토큰이 올바르지 않습니다.")


def latest_by_serial(rows: list[models.WarrantyLookup]) -> list[dict]:
    """시리얼(대문자)별 최근 조회 1건. rows 는 최신순이어야 한다."""
    out: dict[str, dict] = {}
    for r in rows:
        serial = r.serial_tag.strip().upper()
        if not serial or serial in out:
            continue
        out[serial] = {
            "serial": serial,
            "vendor": r.vendor,
            "start_date": r.start_date.isoformat() if r.start_date else None,
            "end_date": r.end_date.isoformat(),
            "service_level": r.service_level,
            "product_name": r.product_name,
            "looked_up_at": r.updated_at.isoformat() if r.updated_at else None,
        }
    return list(out.values())


@router.get("/warranties", dependencies=[Depends(require_integration_token)])
async def list_warranties(db: AsyncSession = Depends(get_db)):
    """
    종료일이 확인된 조회 결과 전체. 대기·미발견·삭제 건은 빠진다.
    재조회 대기 중이거나 재조회가 오류로 끝난 건은 이전에 확인된 값을 그대로 내보낸다.
    """
    rows = (await db.execute(
        select(models.WarrantyLookup)
        .where(models.WarrantyLookup.is_deleted == False,  # noqa: E712
               models.WarrantyLookup.end_date.is_not(None))
        .order_by(models.WarrantyLookup.updated_at.desc(), models.WarrantyLookup.id.desc())
    )).scalars().all()
    return ResponseEnvelope(data=latest_by_serial(list(rows)))
