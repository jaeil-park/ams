"""
app/services/system_log.py — SystemLog 기록 유틸
- FastAPI 전역 예외 핸들러(main.py)에서 호출되어, 요청 실패를 자동 기록합니다.
- 요청을 처리하던 DB 세션이 이미 오류 상태일 수 있으므로 항상 새 세션을 사용합니다.
- 기록 자체가 실패해도 원래 요청/응답 흐름에는 영향을 주지 않습니다 (조용히 무시).
"""

import logging

from fastapi import Request
from jose import JWTError, jwt

from app.core.config import settings
from app.db.session import async_session
from app.models.system_log import SystemLog

logger = logging.getLogger(__name__)

# 로그를 남길 상태 코드: 5xx(서버 오류)는 전부, 4xx는 라우트/스키마 불일치를 주로 나타내는
# 404·422만 대상으로 한다 — 중복 코드/재고 부족 같은 정상적인 비즈니스 검증(400)이나
# 로그인 실패·세션 만료(401/403)는 노이즈이므로 제외한다.
_LOGGED_STATUS_CODES = {404, 422}


def _extract_user_email(request: Request) -> str | None:
    auth = request.headers.get("authorization")
    if not auth or not auth.lower().startswith("bearer "):
        return None
    token = auth.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


async def record_system_log(
    request: Request,
    *,
    status_code: int,
    message: str | None = None,
    detail: str | None = None,
) -> None:
    """요청 실패를 system_logs 테이블에 기록합니다 (실패해도 조용히 무시)."""
    if status_code < 500 and status_code not in _LOGGED_STATUS_CODES:
        return
    try:
        level = "ERROR" if status_code >= 500 else "WARNING"
        entry = SystemLog(
            level=level,
            method=request.method,
            path=request.url.path,
            status_code=status_code,
            user_email=_extract_user_email(request),
            message=(message or "")[:2000] or None,
            detail=(detail or "")[:5000] or None,
        )
        async with async_session() as session:
            session.add(entry)
            await session.commit()
    except Exception:
        logger.exception("system_logs 기록 실패")
