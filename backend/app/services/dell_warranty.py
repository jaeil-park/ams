"""
app/services/dell_warranty.py — Dell TechDirect Warranty API 연동 서비스

- OAuth2 Client Credentials 로 토큰을 받아 asset-entitlements API 를 호출한다. (한 번에 최대 100개 서비스 태그)
- 키(DELL_API_CLIENT_ID/SECRET)는 서버 환경변수로만 관리한다. (claude_rule.md §9)
- 키가 없으면 configured=False — 호출하는 쪽에서 브라우저 확장 프로그램 대기(WAITING_EXTENSION)로 돌린다.

※ TechDirect API 키 발급 전에는 실제 응답으로 검증하지 못했다. 키를 받으면 먼저
  POST /api/v1/warranty/lookups 로 몇 건 조회해 결과를 확인할 것. (URL 은 config 에서 바꿀 수 있다)
"""

from __future__ import annotations

import logging
import time

import httpx

from app.core.config import settings
from app.services.warranty_parse import summarize_dell_api

logger = logging.getLogger(__name__)

_BATCH = 100


class DellWarrantyService:
    def __init__(self, client_id: str | None = None, client_secret: str | None = None):
        self.client_id = client_id if client_id is not None else settings.DELL_API_CLIENT_ID
        self.client_secret = client_secret if client_secret is not None else settings.DELL_API_CLIENT_SECRET
        self._token: str | None = None
        self._token_exp = 0.0

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    async def _get_token(self, client: httpx.AsyncClient) -> str:
        if self._token and time.time() < self._token_exp - 60:
            return self._token
        r = await client.post(
            settings.DELL_API_TOKEN_URL,
            data={"grant_type": "client_credentials", "client_id": self.client_id,
                  "client_secret": self.client_secret},
        )
        r.raise_for_status()
        body = r.json()
        self._token = body["access_token"]
        self._token_exp = time.time() + int(body.get("expires_in", 3600))
        return self._token

    async def fetch_many(self, service_tags: list[str]) -> dict[str, dict]:
        """
        서비스 태그 목록 → {태그: 결과}.
        결과: {status: DONE|NOT_FOUND|ERROR, start_date, end_date, service_level, product_name, detail, error}
        """
        out: dict[str, dict] = {}
        if not service_tags:
            return out
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                token = await self._get_token(client)
            except Exception as e:  # noqa: BLE001 — 토큰 실패는 요청 전체 실패로 기록
                logger.exception("Dell TechDirect 토큰 발급 실패")
                return {t: {"status": "ERROR", "error": f"Dell API 토큰 발급 실패: {e}"[:500]} for t in service_tags}

            for i in range(0, len(service_tags), _BATCH):
                chunk = service_tags[i:i + _BATCH]
                try:
                    r = await client.get(
                        settings.DELL_API_WARRANTY_URL,
                        params={"servicetags": ",".join(chunk)},
                        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                    )
                    r.raise_for_status()
                    assets = r.json()
                except Exception as e:  # noqa: BLE001
                    logger.exception("Dell TechDirect 조회 실패")
                    for t in chunk:
                        out[t] = {"status": "ERROR", "error": f"Dell API 조회 실패: {e}"[:500]}
                    continue

                by_tag = {str(a.get("serviceTag", "")).upper(): a for a in assets if isinstance(a, dict)}
                for t in chunk:
                    a = by_tag.get(t.upper())
                    if not a:
                        out[t] = {"status": "NOT_FOUND", "error": "Dell API 응답에 없는 서비스 태그"}
                        continue
                    s = summarize_dell_api(a)
                    detail = {
                        "ship_date": a.get("shipDate"),
                        "entitlements": [
                            {"service_level": e.get("serviceLevelDescription"), "type": e.get("entitlementType"),
                             "start": e.get("startDate"), "end": e.get("endDate")}
                            for e in (a.get("entitlements") or [])
                        ],
                    }
                    out[t] = {
                        "status": "DONE" if s["end_date"] else "NOT_FOUND",
                        "start_date": s["start_date"], "end_date": s["end_date"],
                        "service_level": s["service_level"], "product_name": s["product_name"],
                        "detail": detail, "error": None if s["end_date"] else "워런티 정보 없음",
                    }
        logger.info("Dell TechDirect 조회 완료: %d건", len(out))
        return out


dell_service = DellWarrantyService()
